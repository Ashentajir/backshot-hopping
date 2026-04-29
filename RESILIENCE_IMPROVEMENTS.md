# HopShot Client - Resilience Improvements

## Overview
This note summarizes the client-side resilience work: retries, fallback paths, and connection health monitoring.

## Key Changes

### 1. **Enhanced QUIC Client with Exponential Backoff Retry**
**File:** `quic_transport.py`

#### Improvements:
- **Exponential Backoff Mechanism**: Instead of single connection attempts, the client now retries with exponential backoff (500ms → 1s → 2s → 4s → 8s, capped at 10s)
- **Configurable Retry Parameters**:
  - `max_retries`: Number of retry attempts (default: 5)
  - `initial_backoff_ms`: Starting backoff interval (default: 500ms)
  - `connect_timeout`: Extended timeout for unstable networks (up to 8+ seconds)

- **Granular Error Handling**: Different handling for:
  - `socket.timeout` - Connection timeout
  - `ConnectionRefusedError` - Server refused connection
  - General exceptions - Other network errors

```python
# Example: QUIC client with retry support
quic = QUICClient(
    host, port,
    max_retries=5,           # Try up to 5 times
    initial_backoff_ms=500,  # Start with 500ms wait
    connect_timeout=8.0      # 8 second timeout per attempt
)
quic_ok = quic.connect(retry=True)  # Automatically retries
```

### 2. **Intelligent Connection Fallback Strategy**
**File:** `client.py` - `_connect_quic()` method

#### Improvements:
- **Primary Port Retry**: First attempts connection to primary QUIC port with full retries
- **Fallback to Alternate Port**: If primary fails, automatically tries alternate port (typically `server_port`)
- **Cascading Timeout**: Fallback uses slightly longer timeout to account for network issues
- **Metrics Recording**: Each attempt is logged with detailed metrics

```python
# Fallback flow:
1. Try QUIC_PORT with 5 retries (500ms backoff)
   ↓
2. If failed, try SERVER_PORT with 3 retries (1000ms backoff)
   ↓
3. Fall back to raw UDP if both fail
```

### 3. **Increased Probe Timeouts for Unstable Networks**
**File:** `client.py` - `start()` method

#### Improvements:
- **Dynamic Probe Timeout**: 
  ```python
  probe_timeout = max(
      config_timeout,           # User-configured timeout
      max_ping_ms * 1.5         # 1.5x safety margin on max_ping
  )
  ```
- **Longer Probe Count**: Ensures adequate sampling for high-loss networks
- **Result**: Server reachability is verified even on slow/lossy connections

### 4. **Automatic Connection Health Monitoring**
**File:** `client.py` - `_check_and_recover_quic()` method

#### Improvements:
- **Periodic Health Checks**: Every 60 seconds, the client verifies QUIC connection status
- **Automatic Reconnection**: If connection is lost, initiates recovery:
  - Detects when QUIC connection becomes inactive
  - Triggers reconnection with appropriate timeout
  - Records recovery metrics for debugging
  
- **Graceful Degradation**: If QUIC recovery fails, system continues with raw UDP

```python
# Health check flow (runs every 60 seconds):
if QUIC_connected:
    ✓ Connection OK, continue
else:
    ⚠ Connection lost, attempt recovery with:
      - 3 retry attempts
      - 1000ms initial backoff
      - Extended timeout
```

### 5. **Enhanced Monitor Loop**
**File:** `client.py` - `_monitor_loop()` method

#### Improvements:
- **Dual-Purpose Monitoring**:
  1. Original: Re-probe every 30s to detect mode changes
  2. New: Health check QUIC every 60s for recovery
  
- **Efficient Resource Usage**: Staggered checks prevent resource exhaustion
- **Continuous Adaptation**: Automatically switches between QUIC and raw UDP based on health

## Network Conditions Handled

✅ **Unstable Ping (High Latency)**
- Extended timeouts up to 8+ seconds per attempt
- Multiple retries with backoff prevent giving up too early

✅ **Packet Loss**
- Exponential backoff reduces retry storms
- Multiple destination support (burst across IPs)
- FEC encoding for packet recovery

✅ **Firewall Port Blocking**
- Automatic fallback to alternate ports
- Port hopping strategy with deterministic ports

✅ **Server Temporary Unreachability**
- Retries with exponential backoff
- Health monitoring for detection
- Automatic recovery when server comes back online

✅ **Intermittent Connectivity**
- Raw UDP fallback when QUIC fails
- Dual-stack transmission (QUIC + UDP simultaneously)
- ARQ selective retransmission

## Configuration Recommendations

### For unstable networks:
```json
{
  "profile": "reliable",
  "max_ping_ms": 15000,
  "probe_timeout_ms": 20000,
  "probe_count": 30,
  "keepalive_interval_sec": 10,
  "adaptive_mode": true,
  "fec_k": 4,
  "fec_m": 4
}
```

### For mobile networks:
```json
{
  "profile": "mobile",
  "max_ping_ms": 10000,
  "probe_timeout_ms": 15000,
  "keepalive_interval_sec": 8,
  "preemptive_hop_ms": 900,
  "reactive_probe": true
}
```

## Metrics & Monitoring

New metrics recorded:
- `quic_connect`: Connection attempts with timeout info
- `quic_recovery`: Health check results and recovery status
- `monitor_probe`: Periodic re-probing results
- Mode changes due to network conditions

## Testing Recommendations

1. **Test with Unstable Networks**:
   ```bash
   # Use network simulation tools (tc, netem, etc.)
   tc qdisc add dev eth0 root netem delay 100ms loss 10%
   ```

2. **Test Server Downtime**:
   ```bash
   # Verify client attempts recovery after server restart
   ```

3. **Test Port Blocking**:
   ```bash
   # Block primary port to trigger fallback
   iptables -A INPUT -p tcp --dport 10001 -j DROP
   ```

## Support

If connection issues persist:
1. Enable verbose logging: `--verbose`
2. Save metrics: `--metrics-file metrics.jsonl`
3. Check firewall rules on your host
4. Test with `--profile reliable` first
5. Review this note for the retry and fallback behavior

**Result**: the client is designed to recover automatically from temporary network interruptions.
