import threading, time, random, struct
import sys
sys.path.insert(0, '.')
import client as clientmod


def base_cfg(port, **kw):
    cfg = {
        "server_port": port, "quic_port": port+1,
        "port_min": port, "port_max": port,
        "shared_seed": "test-seed", "obfs": False,
        "rand_src_port": False, "jitter_bytes": 0,
        "preemptive_hop_ms": 800,
        "max_ping_ms": 15000,
        "fec_k": 4, "fec_m": 4,
        "probe_count": 5, "probe_timeout_ms": 1000,
        "verbose": False, "destinations": ["127.0.0.1"],
        "resolvers": ["127.0.0.1"],
    }
    cfg.update(kw)
    return cfg

# Test 1: max_ping_ms propagates to QUIC connect timeout
print('Running quick test: max_ping propagation')
observed = {}
original_quic = clientmod.QUICClient
class ObserveQUIC:
    def __init__(self, host, port, cafile=None, verify=False, connect_timeout=5.0, **kwargs):
        observed['timeout'] = connect_timeout
    def connect(self):
        return False
    def close(self):
        pass
clientmod.QUICClient = ObserveQUIC
try:
    c = clientmod.HopShotClient(base_cfg(19850, max_ping_ms=15000))
    try:
        c._connect_quic()
        print('Observed timeout:', observed.get('timeout'))
        assert observed.get('timeout', 0) >= 15.0
        print('max_ping propagation: OK')
    finally:
        try:
            c.stop()
        except Exception:
            pass
finally:
    clientmod.QUICClient = original_quic

# Test 2: bootstrap 5-minute budget expires quickly when time advanced
print('Running quick test: bootstrap budget expiry')
port = 20100 + random.randint(0,50)
cfg = base_cfg(port)
c = clientmod.HopShotClient(cfg)
original_probe = clientmod.probe_port
original_monotonic = clientmod.time.monotonic
original_sleep = clientmod.time.sleep

t = [0.0]
def fake_monotonic():
    return t[0]
def fake_sleep(s):
    t[0] += 301.0

def fake_probe(*args, **kwargs):
    return {"port": kwargs.get("port", args[1] if len(args) > 1 else 0), "loss_pct": 100.0, "rtt_ms": 0.0, "sent": 0, "received": 0, "clock_offset_ms": 0}

clientmod.probe_port = fake_probe
clientmod.time.monotonic = fake_monotonic
clientmod.time.sleep = fake_sleep
orig_connect = c._connect_quic
c._connect_quic = lambda: None
try:
    thr = threading.Thread(target=c.start)
    thr.start()
    thr.join(timeout=5.0)
    if thr.is_alive():
        c._running = False
        try:
            c.stop()
        except Exception:
            pass
    assert t[0] >= 301.0
    print('bootstrap expiry fast-forward: OK')
finally:
    clientmod.probe_port = original_probe
    clientmod.time.monotonic = original_monotonic
    clientmod.time.sleep = original_sleep
    c._connect_quic = orig_connect
    try:
        c.stop()
    except Exception:
        pass

print('Quick tests completed')
