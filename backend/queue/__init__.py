from __future__ import annotations

"""Job queue + store abstractions (Sprint 8.3).

Configuration-driven backends: in-memory (default) and an optional, fail-safe
Redis backend. Business logic never depends on the concrete backend.
"""

from backend.queue.config import QueueConfig, get_queue_config, reset_queue_config
from backend.queue.interfaces import JobQueue, JobStore
from backend.queue.factory import build_queue, build_store, reset_queue_backends

__all__ = [
    "QueueConfig",
    "get_queue_config",
    "reset_queue_config",
    "JobQueue",
    "JobStore",
    "build_queue",
    "build_store",
    "reset_queue_backends",
]
