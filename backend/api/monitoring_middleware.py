from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.config.settings import get_app_settings
from backend.logging.logger import bind_context, clear_context
from backend.logging.request_logger import log_request_completed, log_request_started
from backend.monitoring.metrics import record_api_request
from backend.monitoring.tracing import end_trace, start_trace


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Request logging, metrics, and trace context (Sprint 8.5)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_app_settings()
        request_id = request.headers.get(settings.request_id_header) or f"req_{uuid.uuid4().hex[:12]}"
        correlation_id = request.headers.get(settings.correlation_id_header) or request_id
        trace_id = start_trace()

        user_id = ""
        user = getattr(request.state, "user", None)
        if user is not None:
            user_id = getattr(user, "user_id", "") or ""

        bind_context(
            request_id=request_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
            user_id=user_id or None,
        )
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.trace_id = trace_id

        started = time.perf_counter()
        log_request_started(method=request.method, path=request.url.path, request_id=request_id, user_id=user_id)
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000.0
            record_api_request(method=request.method, path=request.url.path, status_code=500, duration_ms=duration_ms)
            clear_context()
            raise

        duration_ms = (time.perf_counter() - started) * 1000.0
        response.headers[settings.request_id_header] = request_id
        response.headers[settings.correlation_id_header] = correlation_id
        response.headers["X-Trace-ID"] = trace_id
        log_request_completed(
            method=request.method,
            path=request.url.path,
            request_id=request_id,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
        )
        record_api_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        end_trace()
        clear_context()
        return response
