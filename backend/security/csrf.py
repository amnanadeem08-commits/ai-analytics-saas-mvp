from __future__ import annotations

"""CSRF protection middleware (Sprint 8.7)."""

import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_CSRF_HEADER = "X-CSRF-Token"
_CSRF_COOKIE = "csrf_token"


def csrf_enabled() -> bool:
    return os.getenv("CSRF_ENABLED", "false").lower() in ("1", "true", "yes")


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not csrf_enabled():
            return await call_next(request)
        if request.method in _SAFE_METHODS:
            response = await call_next(request)
            if _CSRF_COOKIE not in request.cookies:
                token = secrets.token_urlsafe(32)
                response.set_cookie(
                    _CSRF_COOKIE,
                    token,
                    httponly=False,
                    samesite="strict",
                    secure=os.getenv("COOKIE_SECURE", "false").lower() in ("1", "true", "yes"),
                )
            return response
        cookie_token = request.cookies.get(_CSRF_COOKIE, "")
        header_token = request.headers.get(_CSRF_HEADER, "")
        if not cookie_token or cookie_token != header_token:
            return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
        return await call_next(request)
