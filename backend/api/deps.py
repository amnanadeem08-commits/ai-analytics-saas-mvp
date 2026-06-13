from fastapi import HTTPException

from backend.core.exceptions import DatasetNotFoundError, FileValidationError


def map_app_error(exc: Exception) -> HTTPException:
    """Map predictable app exceptions into API-friendly HTTP errors."""
    if isinstance(exc, DatasetNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, FileValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Internal server error")
