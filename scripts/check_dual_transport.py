import sys
sys.path.insert(0, '.')
import client as clientmod


def base_cfg(port, **kw):
    cfg = {
        "server_port": port,
        "quic_port": port + 1,
        "port_min": port,
        "port_max": port,
        "shared_seed": "test-seed",
        "obfs": False,
        "rand_src_port": False,
        "jitter_bytes": 0,
        "preemptive_hop_ms": 800,
        "max_ping_ms": 15000,
        "fec_k": 4,
        "fec_m": 4,
        "probe_count": 5,
        "probe_timeout_ms": 1000,
        "verbose": False,
        "destinations": ["127.0.0.1"],
        "resolvers": ["127.0.0.1"],
    }
    cfg.update(kw)
    return cfg


class FakeQUIC:
    def __init__(self):
        self.sent = 0
        self.connected = True
    def send(self, payload):
        self.sent += 1
    def close(self):
        pass


c = clientmod.HopShotClient(base_cfg(21000))
udp_calls = {"count": 0}
orig_burst = c._burst_send
try:
    def fake_burst(*args, **kwargs):
        udp_calls["count"] += 1

    c._burst_send = fake_burst
    c.quic = FakeQUIC()
    c.quic_ok = True
    c._running = True
    c.send(b"dual-transport-check")

    print(f"udp_burst_calls={udp_calls['count']}")
    print(f"quic_send_calls={c.quic.sent}")
    if udp_calls["count"] > 0 and c.quic.sent > 0:
        print("OK: send() used UDP raw burst and QUIC in parallel")
    else:
        raise SystemExit("FAIL: dual transport path not active")
finally:
    c._burst_send = orig_burst
    try:
        c.stop()
    except Exception:
        pass
