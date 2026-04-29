# HopShot Server Deployment Quick Guide

Use `README.md` for the main overview. This file is a short server-only checklist.

## What you need

- Linux VPS or server host
- Root or sudo access
- Python 3.10+
- The same `shared_seed` on server and client

## Quick deploy

```bash
python3 deploy.py genkey
python3 deploy.py server --easy --prepare-only
python3 deploy.py server --easy
```

## Minimal `server.config.json`

```json
{
  "listen_port": 10000,
  "quic_port": 10001,
  "port_min": 10000,
  "port_max": 65000,
  "shared_seed": "PASTE_THE_SAME_SEED_AS_CLIENT",
  "service_mode": "tunnel",
  "tunnel_mode": "udp",
  "setup_iptables": true,
  "keepalive_interval_sec": 15,
  "log_file": "server.log"
}
```

## Open ports

```bash
sudo ufw allow 10000/udp
sudo ufw allow 10001/tcp
sudo ufw allow 10000:65000/udp
```

If you want port hopping to work well on Linux, enable iptables redirect:

```bash
sudo iptables -t nat -A PREROUTING -p udp \
  --dport 10000:65000 -j REDIRECT --to-port 10000
```

## Run as a service

```ini
[Unit]
Description=HopShot Server
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/hopshot
ExecStart=/usr/bin/python3 /opt/hopshot/deploy.py server --config /opt/hopshot/server.config.json
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

## Verify

```bash
ss -ulnp | grep 10000
tail -f server.log
```

## Notes

- Use `adaptive_tunnel_on_demand: true` and `adaptive_proxy_on_demand: true` for flexible client behavior.
- `tun`/`tap` with `--tunnel-default-route` is the full-PC VPN path.
- `udp` tunnel mode is relay-only.
