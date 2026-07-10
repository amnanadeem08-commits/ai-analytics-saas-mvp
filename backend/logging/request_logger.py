from __future__ import annotations

from backend.logging.logger import get_logger

_log = get_logger("ai_analytics.request")


def log_request_started(*, method: str, path: str, request_id: str, **ctx) -> None:
    _log.info("request_started", extra={"event": "request_started", "method": method, "path": path, "request_id": request_id, **ctx})


def log_request_completed(*, method: str, path: str, request_id: str, status_code: int, duration_ms: float, **ctx) -> None:
    _log.info(
        "request_completed",
        extra={
            "event": "request_completed",
            "method": method,
            "path": path,
            "request_id": request_id,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 3),
            **ctx,
        },
    )
