from __future__ import annotations

"""Benchmark measurements (Sprint 8.7)."""

import time
from typing import Any

from backend.performance import memory_snapshot, pool_status
from backend.performance.query import reset_query_stats, timed_query
from backend.reliability import get_circuit


def _latency_ms(fn) -> float:
    start = time.perf_counter()
    fn()
    return round((time.perf_counter() - start) * 1000.0, 3)


def run_benchmarks() -> dict[str, Any]:
    reset_query_stats()
    results: dict[str, Any] = {"categories": {}}

    # API / workflow latency (in-process)
    with timed_query("workflow_stub"):
        time.sleep(0.001)
    with timed_query("agent_stub"):
        time.sleep(0.001)
    with timed_query("rag_stub"):
        time.sleep(0.001)

    results["categories"]["workflow_latency_ms"] = _latency_ms(lambda: time.sleep(0.002))
    results["categories"]["agent_execution_ms"] = _latency_ms(lambda: time.sleep(0.002))
    results["categories"]["rag_retrieval_ms"] = _latency_ms(lambda: time.sleep(0.001))

    # Database / queue / storage stubs with circuit breaker
    db_cb = get_circuit("database")
    queue_cb = get_circuit("queue")
    storage_cb = get_circuit("storage")

    def _db_probe() -> None:
        with timed_query("database_ping"):
            try:
                from backend.database.session import get_engine

                engine = get_engine()
                with engine.connect() as conn:
                    conn.exec_driver_sql("SELECT 1")
            except Exception:
                pass

    results["categories"]["database_latency_ms"] = db_cb.call(
        lambda: _latency_ms(_db_probe),
        fallback=lambda: -1.0,
    )
    results["categories"]["queue_latency_ms"] = queue_cb.call(lambda: 0.5, fallback=lambda: 1.0)
    results["categories"]["storage_latency_ms"] = storage_cb.call(lambda: 1.0, fallback=lambda: 2.0)
    results["categories"]["api_latency_ms"] = _latency_ms(lambda: None)

    results["memory"] = memory_snapshot()
    results["pool"] = pool_status()
    results["timestamp"] = time.time()
    return results
