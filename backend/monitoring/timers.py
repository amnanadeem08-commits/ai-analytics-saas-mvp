from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from backend.monitoring.counters import observe_timer


@contextmanager
def timer(name: str, *, labels: dict[str, str] | None = None) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    finally:
        observe_timer(name, (time.perf_counter() - started) * 1000.0, labels=labels)
