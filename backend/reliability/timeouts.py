from __future__ import annotations

"""Timeout handling (Sprint 8.7)."""

import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


async def with_timeout(coro: Awaitable[T], *, seconds: float) -> T:
    return await asyncio.wait_for(coro, timeout=seconds)


def run_with_timeout(fn: Callable[[], T], *, seconds: float) -> T:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=seconds)
        except FuturesTimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"Operation timed out after {seconds}s") from exc
