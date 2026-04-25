"""
Shared terminal UI helpers for HopShot.

Provides ANSI color formatting and configurable logging setup for both the
client and server CLIs without external dependencies.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
COLORS = {
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan": "\x1b[36m",
    "white": "\x1b[37m",
}
LEVEL_COLORS = {
    logging.DEBUG: COLORS["cyan"],
    logging.INFO: COLORS["green"],
    logging.WARNING: COLORS["yellow"],
    logging.ERROR: COLORS["red"],
    logging.CRITICAL: COLORS["magenta"],
}


def supports_color(stream=None) -> bool:
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    try:
        return stream.isatty()
    except Exception:
        return False


def colorize(text: str, color_name: str = "", bold: bool = False, dim: bool = False,
             use_color: bool = True) -> str:
    if not use_color:
        return text
    prefix = ""
    if bold:
        prefix += BOLD
    if dim:
        prefix += DIM
    prefix += COLORS.get(color_name, "")
    if not prefix:
        return text
    return f"{prefix}{text}{RESET}"


def title(text: str, color_name: str = "cyan", use_color: bool = True) -> str:
    return colorize(text, color_name, bold=True, use_color=use_color)


def section_header(text: str, color_name: str = "cyan", use_color: bool = True) -> str:
    return colorize(f"[ {text} ]", color_name, bold=True, use_color=use_color)


def key_value(key: str, value, key_color: str = "cyan", value_color: str = None,
              use_color: bool = True, width: int = 18) -> str:
    key_text = colorize(f"{key:<{width}}", key_color, bold=True, use_color=use_color)
    value_text = str(value)
    if value_color:
        value_text = colorize(value_text, value_color, bold=True, use_color=use_color)
    return f"{key_text} {value_text}"


class ColorFormatter(logging.Formatter):
    def __init__(self, use_color: bool = True):
        super().__init__()
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%H:%M:%S")
        level = f"{record.levelname:<8}"
        name = record.name
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"

        if self.use_color and record.levelno in LEVEL_COLORS:
            level = f"{LEVEL_COLORS[record.levelno]}{level}{RESET}"
            name = colorize(name, "blue", bold=True, use_color=True)
            timestamp = colorize(timestamp, "white", dim=True, use_color=True)
        return f"{timestamp} [{level}] {name}: {message}"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.threadName,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(verbose: bool = False, log_file: str = None,
                      json_logs: bool = False, stream=None):
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)

    stream = stream or sys.stdout
    stream_handler = logging.StreamHandler(stream)
    stream_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    stream_handler.setFormatter(ColorFormatter(use_color=supports_color(stream) and not json_logs))
    root.addHandler(stream_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JsonFormatter() if json_logs else ColorFormatter(use_color=False))
        root.addHandler(file_handler)
