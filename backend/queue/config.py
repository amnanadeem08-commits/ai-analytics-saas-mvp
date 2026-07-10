from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass
class QueueConfig:
    """Environment-driven queue configuration."""

    backend: str = field(default_factory=lambda: os.getenv("QUEUE_BACKEND", "memory").strip().lower())
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
    namespace: str = field(default_factory=lambda: os.getenv("QUEUE_NAMESPACE", "databot"))
    default_max_retries: int = field(default_factory=lambda: _int_env("JOB_MAX_RETRIES", 3))
    worker_poll_interval_ms: int = field(default_factory=lambda: _int_env("WORKER_POLL_INTERVAL_MS", 200))
    worker_heartbeat_ms: int = field(default_factory=lambda: _int_env("WORKER_HEARTBEAT_MS", 1000))

    @property
    def uses_redis(self) -> bool:
        return self.backend in {"redis"}


_CONFIG: QueueConfig | None = None


def get_queue_config(*, refresh: bool = False) -> QueueConfig:
    global _CONFIG
    if _CONFIG is None or refresh:
        _CONFIG = QueueConfig()
    return _CONFIG


def reset_queue_config() -> None:
    global _CONFIG
    _CONFIG = None
