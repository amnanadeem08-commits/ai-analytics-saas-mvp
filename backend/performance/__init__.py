from __future__ import annotations

import tracemalloc

from backend.performance.cache import TTLCache, cached, get_cache, reset_cache
from backend.performance.compression import gzip_json_response, should_compress
from backend.performance.pagination import PageParams, PaginatedResult, lazy_slice, paginate
from backend.performance.pooling import optimize_pool_config, pool_status
from backend.performance.query import explain_slow_queries, query_stats, reset_query_stats, timed_query
from backend.performance.streaming import chunk_file, stream_bytes

__all__ = [
    "TTLCache",
    "get_cache",
    "reset_cache",
    "cached",
    "PageParams",
    "PaginatedResult",
    "paginate",
    "lazy_slice",
    "gzip_json_response",
    "should_compress",
    "optimize_pool_config",
    "pool_status",
    "timed_query",
    "query_stats",
    "reset_query_stats",
    "explain_slow_queries",
    "stream_bytes",
    "chunk_file",
    "memory_snapshot",
]


def memory_snapshot() -> dict[str, int]:
    if not tracemalloc.is_tracing():
        tracemalloc.start()
    current, peak = tracemalloc.get_traced_memory()
    return {"current_bytes": current, "peak_bytes": peak}
