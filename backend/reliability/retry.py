from __future__ import annotations

"""Retry policies (Sprint 8.7)."""

import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")


def retry(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    jitter: bool = True,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except retry_on as exc:
            last_exc = exc
            if attempt >= attempts - 1:
                break
            delay = min(max_delay, base_delay * (2**attempt))
            if jitter:
                delay *= 0.5 + random.random()
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc
