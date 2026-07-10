from __future__ import annotations

"""Health recovery helpers (Sprint 8.7)."""

from typing import Any

from backend.reliability.circuit_breaker import get_circuit


def attempt_recovery() -> dict[str, Any]:
    """Reset circuit breakers and return post-recovery health snapshot."""
    results: dict[str, Any] = {"recovered": []}
    for name in ("database", "queue", "storage"):
        cb = get_circuit(name)
        if cb.state.value != "closed":
            cb.reset()
            results["recovered"].append(name)
    try:
        from backend.monitoring.health import health_report

        results["health"] = health_report()
    except Exception as exc:
        results["health_error"] = str(exc)
    return results
