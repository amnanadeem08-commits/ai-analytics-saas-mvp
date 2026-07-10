from __future__ import annotations

"""Authentication middleware (Sprint 8.0).

Non-blocking identity attachment: when a valid bearer token is present, the
resolved user is attached to ``request.state.user``. Route-level 401 enforcement
is handled by the `get_current_user_dependency` dependency, not this middleware,
so public endpoints (health, docs, AI routes) keep working unchanged.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.services.auth_service import AuthError, get_current_user


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.user = None
        request.state.auth_error = None
        auth_header = request.headers.get("authorization", "")
        token = ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        elif request.cookies.get("access_token"):
            token = request.cookies["access_token"]

        if token:
            try:
                request.state.user = get_current_user(token)
            except AuthError as exc:
                # Do not block here — let protected routes enforce 401 via dependency.
                request.state.auth_error = exc.message
        return await call_next(request)
