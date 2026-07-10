from __future__ import annotations

"""Repository query optimization helpers (Sprint 8.7)."""

from typing import Any, Sequence, TypeVar

from backend.performance.pagination import paginate
from backend.performance.query import timed_query

T = TypeVar("T")


def optimized_list(
    items: Sequence[T],
    *,
    page: int = 1,
    page_size: int = 50,
    query_name: str = "list",
) -> dict[str, Any]:
    with timed_query(query_name):
        page_result = paginate(items, page=page, page_size=page_size)
    return page_result.model_dump()
