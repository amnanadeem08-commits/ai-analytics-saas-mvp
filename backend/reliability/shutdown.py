from __future__ import annotations

"""Graceful shutdown + resource cleanup (Sprint 8.7)."""

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

_SHUTDOWN_HOOKS: list[Callable[[], None | Awaitable[None]]] = []
_SHUTTING_DOWN = False


def register_shutdown_hook(hook: Callable[[], None | Awaitable[None]]) -> None:
    _SHUTDOWN_HOOKS.append(hook)


def is_shutting_down() -> bool:
    return _SHUTTING_DOWN


async def run_shutdown() -> None:
    global _SHUTTING_DOWN
    _SHUTTING_DOWN = True
    logger.info("Graceful shutdown started (%d hooks)", len(_SHUTDOWN_HOOKS))
    for hook in reversed(_SHUTDOWN_HOOKS):
        try:
            result = hook()
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            logger.exception("Shutdown hook failed")
    try:
        from backend.database.session import dispose_engine

        dispose_engine()
    except Exception:
        logger.exception("Engine dispose failed")
    try:
        from backend.performance import reset_cache

        reset_cache()
    except Exception:
        pass
    logger.info("Graceful shutdown complete")


def reset_shutdown_state() -> None:
    global _SHUTTING_DOWN
    _SHUTTING_DOWN = False
    _SHUTDOWN_HOOKS.clear()
