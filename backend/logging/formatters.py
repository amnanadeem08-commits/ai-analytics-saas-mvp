from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter (Sprint 8.5)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "request_id",
            "correlation_id",
            "trace_id",
            "span_id",
            "workflow_id",
            "job_id",
            "user_id",
            "organization_id",
            "workspace_id",
            "event",
        ):
            value = getattr(record, key, None)
            if value:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        ctx_parts = []
        for key in ("request_id", "workflow_id", "job_id", "user_id"):
            value = getattr(record, key, None)
            if value:
                ctx_parts.append(f"{key}={value}")
        if ctx_parts:
            return f"{base} [{' '.join(ctx_parts)}]"
        return base
