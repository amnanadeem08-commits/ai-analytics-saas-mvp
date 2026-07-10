from __future__ import annotations

"""Brute-force protection for authentication (Sprint 8.7)."""

import os
import threading
import time
from collections import defaultdict

_LOCK = threading.RLock()
_FAILURES: dict[str, list[float]] = defaultdict(list)
_LOCKOUTS: dict[str, float] = {}


def _max_attempts() -> int:
    return int(os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "5"))


def _lockout_seconds() -> float:
    return float(os.getenv("AUTH_LOCKOUT_SECONDS", "300"))


def _window_seconds() -> float:
    return float(os.getenv("AUTH_FAILURE_WINDOW_SECONDS", "900"))


def is_locked(identifier: str) -> bool:
    with _LOCK:
        until = _LOCKOUTS.get(identifier)
        if until is None:
            return False
        if time.monotonic() >= until:
            _LOCKOUTS.pop(identifier, None)
            _FAILURES.pop(identifier, None)
            return False
        return True


def record_failure(identifier: str) -> None:
    now = time.monotonic()
    with _LOCK:
        bucket = _FAILURES[identifier]
        bucket[:] = [t for t in bucket if now - t <= _window_seconds()]
        bucket.append(now)
        if len(bucket) >= _max_attempts():
            _LOCKOUTS[identifier] = now + _lockout_seconds()


def record_success(identifier: str) -> None:
    with _LOCK:
        _FAILURES.pop(identifier, None)
        _LOCKOUTS.pop(identifier, None)


def lockout_remaining(identifier: str) -> float:
    with _LOCK:
        until = _LOCKOUTS.get(identifier)
        if until is None:
            return 0.0
        return max(0.0, until - time.monotonic())


def reset_brute_force_state() -> None:
    with _LOCK:
        _FAILURES.clear()
        _LOCKOUTS.clear()
