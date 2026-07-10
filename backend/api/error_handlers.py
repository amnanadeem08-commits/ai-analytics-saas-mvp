from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def error_payload(
    *,
    error: str,
    details: Any = None,
    status_code: int = 400,
) -> dict[str, Any]:
    return {
        "success": False,
        "error": error,
        "details": details,
        "status_code": status_code,
    }


def register_error_handlers(app: FastAPI) -> None:
    """Attach structured JSON error handlers to the FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(
                error="Validation error",
                details=exc.errors(),
                status_code=422,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            body = {"success": False, **detail}
            body.setdefault("status_code", exc.status_code)
            return JSONResponse(status_code=exc.status_code, content=body)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                error=str(detail),
                details=None,
                status_code=exc.status_code,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        from backend.monitoring.errors import capture_exception, record_unhandled

        record_unhandled(request.url.path, exc)
        capture_exception(exc, context={"path": request.url.path})
        logger.exception("Unhandled API error on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content=error_payload(
                error="Internal server error",
                details=str(exc),
                status_code=500,
            ),
        )


def raise_api_error(
    status_code: int,
    error: str,
    *,
    details: Any = None,
) -> None:
    """Raise an HTTPException with the standard structured payload."""
    raise HTTPException(
        status_code=status_code,
        detail=error_payload(error=error, details=details, status_code=status_code),
    )


def map_service_exception(exc: Exception) -> HTTPException:
    """Map common service exceptions to structured HTTP errors."""
    if isinstance(exc, KeyError):
        return HTTPException(
            status_code=404,
            detail=error_payload(error=str(exc) or "Not found", status_code=404),
        )
    if isinstance(exc, FileNotFoundError):
        return HTTPException(
            status_code=404,
            detail=error_payload(error=str(exc), status_code=404),
        )
    if isinstance(exc, (ValueError, TypeError)):
        return HTTPException(
            status_code=400,
            detail=error_payload(error=str(exc), status_code=400),
        )
    logger.exception("Unhandled service error: %s", exc)
    return HTTPException(
        status_code=500,
        detail=error_payload(
            error="Internal server error",
            details=str(exc),
            status_code=500,
        ),
    )
