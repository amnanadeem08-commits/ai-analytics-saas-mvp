from __future__ import annotations

"""Rate limiting (Sprint 8.7)."""

import os
import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimiter:
    def __init__(self, *, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.RLock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > self.window:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_GLOBAL_LIMITER: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _GLOBAL_LIMITER
    if _GLOBAL_LIMITER is None:
        limit = int(os.getenv("RATE_LIMIT_REQUESTS", "120"))
        window = float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        _GLOBAL_LIMITER = RateLimiter(limit=limit, window_seconds=window)
    return _GLOBAL_LIMITER


def reset_rate_limiter() -> None:
    global _GLOBAL_LIMITER
    if _GLOBAL_LIMITER:
        _GLOBAL_LIMITER.reset()
    _GLOBAL_LIMITER = None


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in (
            "/health",
            "/api/v1/monitoring/health",
            "/api/v1/monitoring/ready",
            "/api/v1/ready",
            "/api/v1/live",
        ):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        key = f"{client}:{request.url.path}"
        if not get_rate_limiter().allow(key):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(int(get_rate_limiter().window))},
            )
        return await call_next(request)
