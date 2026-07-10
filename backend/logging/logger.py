from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

from backend.logging.handlers import configure_root_logging

_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})


def bind_context(**fields: Any) -> dict[str, Any]:
    current = dict(_log_context.get({}))
    current.update({k: v for k, v in fields.items() if v is not None})
    _log_context.set(current)
    return current


def clear_context() -> None:
    _log_context.set({})


def get_context() -> dict[str, Any]:
    return dict(_log_context.get({}))


class ContextAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        ctx = get_context()
        for key, value in ctx.items():
            extra[key] = value
        adapter_extra = self.extra or {}
        for key, value in adapter_extra.items():
            if value is not None:
                extra[key] = value
        return msg, kwargs


def get_logger(name: str, **context: Any) -> ContextAdapter:
    base = logging.getLogger(name)
    return ContextAdapter(base, context)


def setup_logging(*, level: str | None = None, fmt: str | None = None) -> None:
    try:
        from backend.config.settings import get_app_settings

        settings = get_app_settings()
        configure_root_logging(level=level or settings.log_level, fmt=(fmt or settings.log_format))  # type: ignore[arg-type]
    except Exception:
        configure_root_logging(level=level or "INFO", fmt="text")  # type: ignore[arg-type]
