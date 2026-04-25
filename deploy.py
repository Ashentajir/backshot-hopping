#!/usr/bin/env python3
"""Self-installing bootstrapper for HopShot server/client deployments."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"


SERVER_DEFAULT_CONFIG = {
    "listen_port": 10000,
    "quic_port": 10001,
    "port_min": 10000,
    "port_max": 65000,
    "shared_seed": "change-me",
    "obfs": False,
    "masquerade": False,
    "setup_iptables": False,
    "certfile": "hopshot.crt",
    "keyfile": "hopshot.key",
    "declared_down_kbps": 0,
    "verbose": False,
    "jitter_bytes": 64,
    "log_file": "server.log",
    "json_logs": False,
}


CLIENT_DEFAULT_CONFIG = {
    "server_port": 10000,
    "quic_port": 10001,
    "port_min": 10000,
    "port_max": 65000,
    "shared_seed": "change-me",
    "profile": "balanced",
    "obfs": False,
    "rand_src_port": False,
    "jitter_bytes": 64,
    "preemptive_hop_ms": 800,
    "declared_up_kbps": 0,
    "masquerade": False,
    "mtu": 0,
    "fec_k": 4,
    "fec_m": 4,
    "probe_count": 20,
    "probe_timeout_ms": 2000,
    "destinations": ["127.0.0.1"],
    "resolvers": ["1.1.1.1"],
    "verbose": False,
    "log_file": "client.log",
    "json_logs": False,
    "metrics_file": "client.metrics.jsonl",
}


def venv_python_path() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def is_comment_or_blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def requirements_present() -> bool:
    req = ROOT / "requirements.txt"
    if not req.exists():
        return False
    for line in req.read_text(encoding="utf-8").splitlines():
        if not is_comment_or_blank(line):
            return True
    return False


def ensure_venv() -> Path:
    py = venv_python_path()
    if py.exists():
        return py
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
    return venv_python_path()


def install_dependencies(py: Path) -> None:
    subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    if requirements_present():
        subprocess.check_call([str(py), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])


def default_config(role: str) -> dict:
    if role == "server":
        return dict(SERVER_DEFAULT_CONFIG)
    return dict(CLIENT_DEFAULT_CONFIG)


def ensure_config(role: str, config_path: Path) -> None:
    if config_path.exists():
        return
    example = ROOT / f"{role}.config.example.json"
    payload = default_config(role)
    if example.exists():
        shutil.copyfile(example, config_path)
        return
    config_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="HopShot deployment bootstrapper")
    parser.add_argument("role", choices=("server", "client"), help="Which app to prepare and run")
    parser.add_argument("--config", default=None, help="Config file to create/use for the selected role")
    parser.add_argument("--prepare-only", action="store_true", help="Install and create config, but do not launch")
    args, extra = parser.parse_known_args()

    py = ensure_venv()
    install_dependencies(py)

    config_path = Path(args.config) if args.config else ROOT / f"{args.role}.config.json"
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    ensure_config(args.role, config_path)

    if args.prepare_only:
        print(f"Prepared {args.role} environment.")
        print(f"Config: {config_path}")
        print(f"Venv: {VENV_DIR}")
        return 0

    script_path = ROOT / f"{args.role}.py"
    command = [str(py), str(script_path), "--config", str(config_path), *extra]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
