from __future__ import annotations

"""In-memory TTL cache (Sprint 8.7)."""

import threading
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class TTLCache:
    def __init__(self, *, maxsize: int = 256, ttl_seconds: float = 300.0) -> None:
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires, value = entry
            if time.monotonic() > expires:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._data) >= self._maxsize:
                oldest = min(self._data.items(), key=lambda x: x[1][0])[0]
                self._data.pop(oldest, None)
            self._data[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


_GLOBAL_CACHE: TTLCache | None = None


def get_cache(*, maxsize: int = 256, ttl_seconds: float = 300.0) -> TTLCache:
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is None:
        _GLOBAL_CACHE = TTLCache(maxsize=maxsize, ttl_seconds=ttl_seconds)
    return _GLOBAL_CACHE


def reset_cache() -> None:
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is not None:
        _GLOBAL_CACHE.clear()
    _GLOBAL_CACHE = None


def cached(key: str, factory: Callable[[], T], *, ttl_seconds: float | None = None) -> T:
    cache = get_cache()
    hit = cache.get(key)
    if hit is not None:
        return hit  # type: ignore[return-value]
    value = factory()
    cache.set(key, value)
    return value
