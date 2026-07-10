from __future__ import annotations

"""Fallback handling (Sprint 8.7)."""

from typing import Callable, TypeVar

T = TypeVar("T")


def with_fallback(primary: Callable[[], T], fallback: Callable[[], T]) -> T:
    try:
        return primary()
    except Exception:
        return fallback()


async def with_fallback_async(
    primary: Callable[[], T],
    fallback: Callable[[], T],
) -> T:
    try:
        return primary()
    except Exception:
        return fallback()
