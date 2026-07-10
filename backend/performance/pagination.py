from __future__ import annotations

"""Pagination helpers (Sprint 8.7)."""

from typing import Any, Generic, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PageParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class PaginatedResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    items: list[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False


def paginate(items: Sequence[T], *, page: int = 1, page_size: int = 50) -> PaginatedResult:
    total = len(items)
    page = max(1, page)
    page_size = max(1, min(page_size, 500))
    pages = max(1, (total + page_size - 1) // page_size) if total else 0
    start = (page - 1) * page_size
    end = start + page_size
    slice_items = list(items[start:end])
    return PaginatedResult(
        items=slice_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
    )


def lazy_slice(items: Sequence[T], *, offset: int = 0, limit: int = 50) -> list[T]:
    """Lazy-loading window over an in-memory sequence."""
    offset = max(0, offset)
    limit = max(1, min(limit, 500))
    return list(items[offset : offset + limit])
