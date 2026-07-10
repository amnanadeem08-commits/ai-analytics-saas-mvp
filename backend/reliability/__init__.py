from __future__ import annotations

from backend.reliability.circuit_breaker import CircuitBreaker, CircuitState, circuit_status, get_circuit
from backend.reliability.fallback import with_fallback, with_fallback_async
from backend.reliability.retry import retry
from backend.reliability.shutdown import is_shutting_down, register_shutdown_hook, reset_shutdown_state, run_shutdown
from backend.reliability.timeouts import run_with_timeout, with_timeout

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "get_circuit",
    "circuit_status",
    "retry",
    "register_shutdown_hook",
    "run_shutdown",
    "is_shutting_down",
    "reset_shutdown_state",
    "with_timeout",
    "run_with_timeout",
    "with_fallback",
    "with_fallback_async",
]
