from __future__ import annotations

import traceback
from typing import Any

from backend.logging.logger import get_logger
from backend.monitoring.counters import inc_counter
from backend.monitoring.metrics import record_api_request

_log = get_logger("ai_analytics.errors")

ERROR_CATEGORIES = {
    "validation": (ValueError, TypeError),
    "not_found": (KeyError, FileNotFoundError),
    "auth": (),
    "internal": (Exception,),
}


def categorize_exception(exc: Exception) -> str:
    for category, types in ERROR_CATEGORIES.items():
        if types and isinstance(exc, types):
            return category
    name = type(exc).__name__.lower()
    if "auth" in name:
        return "auth"
    if "notfound" in name or "missing" in name:
        return "not_found"
    return "internal"


def capture_exception(exc: Exception, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    category = categorize_exception(exc)
    payload = {
        "category": category,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "traceback": traceback.format_exc(),
        "context": dict(context or {}),
    }
    _log.error("exception_captured", extra={"event": "exception_captured", **payload})
    inc_counter("errors_total", labels={"category": category, "type": type(exc).__name__})
    return payload


def record_unhandled(path: str, exc: Exception) -> None:
    capture_exception(exc, context={"path": path, "handled": False})
    record_api_request(method="*", path=path, status_code=500, duration_ms=0.0)


def recovery_hint(category: str) -> str:
    hints = {
        "validation": "Verify request payload and retry.",
        "not_found": "Check resource identifiers.",
        "auth": "Authenticate and verify permissions.",
        "internal": "Retry later or contact support.",
    }
    return hints.get(category, hints["internal"])
