from __future__ import annotations

import asyncio

import pytest

from backend.reliability.circuit_breaker import CircuitBreaker, CircuitState
from backend.reliability.fallback import with_fallback
from backend.reliability.retry import retry
from backend.reliability.shutdown import reset_shutdown_state, run_shutdown
from backend.reliability.timeouts import run_with_timeout


def setup_function():
    reset_shutdown_state()


def test_circuit_breaker_opens_and_fallback():
    cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.01)

    def boom():
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        cb.call(boom)
    with pytest.raises(RuntimeError):
        cb.call(boom)
    assert cb.state == CircuitState.OPEN
    assert cb.call(boom, fallback=lambda: "ok") == "ok"


def test_retry_eventually_succeeds():
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ValueError("not yet")
        return "done"

    assert retry(flaky, attempts=5, base_delay=0.0, jitter=False) == "done"


def test_with_fallback():
    def primary():
        raise RuntimeError()

    def fallback():
        return 7

    assert with_fallback(primary, fallback) == 7


def test_run_with_timeout():
    with pytest.raises(TimeoutError):
        run_with_timeout(lambda: __import__("time").sleep(0.2), seconds=0.05)


def test_graceful_shutdown_runs_hooks():
    seen = {"ok": False}

    from backend.reliability.shutdown import register_shutdown_hook

    register_shutdown_hook(lambda: seen.update(ok=True))
    asyncio.run(run_shutdown())
    assert seen["ok"] is True
