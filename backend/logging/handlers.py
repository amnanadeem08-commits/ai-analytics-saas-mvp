from __future__ import annotations

import logging
import sys
from typing import Literal

from backend.logging.formatters import JSONFormatter, TextFormatter


def configure_root_logging(*, level: str = "INFO", fmt: Literal["json", "text"] = "json") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter() if fmt == "json" else TextFormatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    ))
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_handler(name: str, *, level: str = "INFO", fmt: str = "json") -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter() if fmt == "json" else TextFormatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    ))
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler.set_name(name)
    return handler
