from __future__ import annotations

"""Query timing + optimization helpers (Sprint 8.7)."""

import time
from contextlib import contextmanager
from typing import Any, Iterator

_QUERY_STATS: list[dict[str, Any]] = []


@contextmanager
def timed_query(name: str) -> Iterator[None]:
    started = time.perf_counter()
    error = ""
    try:
        yield
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        _QUERY_STATS.append({"name": name, "duration_ms": round(elapsed_ms, 3), "error": error})
        if len(_QUERY_STATS) > 500:
            del _QUERY_STATS[:250]


def query_stats() -> list[dict[str, Any]]:
    return list(_QUERY_STATS)


def reset_query_stats() -> None:
    _QUERY_STATS.clear()


def explain_slow_queries(*, threshold_ms: float = 100.0) -> list[dict[str, Any]]:
    return [q for q in _QUERY_STATS if q["duration_ms"] >= threshold_ms and not q.get("error")]
