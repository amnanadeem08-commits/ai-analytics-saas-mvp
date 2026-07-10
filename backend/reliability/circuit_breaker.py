from __future__ import annotations

"""Circuit breaker abstraction (Sprint 8.7)."""

import threading
import time
from enum import Enum
from typing import Callable, TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        *,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = 0.0
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._opened_at >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
            return self._state

    def call(self, fn: Callable[[], T], *, fallback: Callable[[], T] | None = None) -> T:
        state = self.state
        if state == CircuitState.OPEN:
            if fallback:
                return fallback()
            raise RuntimeError(f"Circuit '{self.name}' is open")
        try:
            result = fn()
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            if fallback:
                return fallback()
            raise

    def reset(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED
            self._opened_at = 0.0

    def _on_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()

    def status(self) -> dict[str, object]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self._failures,
            "failure_threshold": self.failure_threshold,
        }


_REGISTRY: dict[str, CircuitBreaker] = {}


def get_circuit(name: str, **kwargs: object) -> CircuitBreaker:
    if name not in _REGISTRY:
        _REGISTRY[name] = CircuitBreaker(name=name, **kwargs)  # type: ignore[arg-type]
    return _REGISTRY[name]


def circuit_status() -> list[dict[str, object]]:
    return [cb.status() for cb in _REGISTRY.values()]
