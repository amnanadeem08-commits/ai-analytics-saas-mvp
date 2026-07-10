from __future__ import annotations

"""Queue/store factory with configuration-driven selection + safe fallback."""

import logging

from backend.queue.config import get_queue_config
from backend.queue.interfaces import JobQueue, JobStore
from backend.queue.memory import InMemoryJobQueue, InMemoryJobStore

_log = logging.getLogger("ai_analytics.queue")

_queue: JobQueue | None = None
_store: JobStore | None = None
_active_backend: str = "memory"


def build_queue() -> JobQueue:
    config = get_queue_config()
    if config.uses_redis:
        try:
            from backend.queue.redis_backend import RedisJobQueue

            return RedisJobQueue(config.redis_url, namespace=config.namespace)
        except Exception as exc:  # noqa: BLE001
            _log.warning("Redis queue unavailable (%s); falling back to in-memory queue.", exc)
    return InMemoryJobQueue()


def build_store() -> JobStore:
    config = get_queue_config()
    if config.uses_redis:
        try:
            from backend.queue.redis_backend import RedisJobStore

            return RedisJobStore(config.redis_url, namespace=config.namespace)
        except Exception as exc:  # noqa: BLE001
            _log.warning("Redis store unavailable (%s); falling back to in-memory store.", exc)
    return InMemoryJobStore()


def get_queue() -> JobQueue:
    global _queue, _active_backend
    if _queue is None:
        _queue = build_queue()
        _active_backend = "redis" if type(_queue).__name__.startswith("Redis") else "memory"
    return _queue


def get_store() -> JobStore:
    global _store
    if _store is None:
        _store = build_store()
    return _store


def active_backend() -> str:
    get_queue()
    return _active_backend


def reset_queue_backends() -> None:
    """Test helper — rebuild queue + store from current configuration."""
    global _queue, _store, _active_backend
    _queue = None
    _store = None
    _active_backend = "memory"
