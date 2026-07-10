from __future__ import annotations

import time

from backend.performance.cache import TTLCache, cached, reset_cache
from backend.performance.pagination import paginate
from backend.performance.repository import optimized_list


def test_ttl_cache_expires():
    cache = TTLCache(maxsize=10, ttl_seconds=0.02)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    time.sleep(0.03)
    assert cache.get("k") is None


def test_cached_factory_called_once():
    reset_cache()
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return 42

    assert cached("x", factory) == 42
    assert cached("x", factory) == 42
    assert calls["n"] == 1


def test_paginate_and_optimized_list():
    items = list(range(120))
    page = paginate(items, page=2, page_size=25)
    assert page.total == 120
    assert len(page.items) == 25
    assert page.has_prev is True
    result = optimized_list(items, page=1, page_size=10, query_name="test_list")
    assert result["total"] == 120
    assert len(result["items"]) == 10
