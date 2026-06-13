class AppError(Exception):
    """Base exception for predictable application errors."""


class FileValidationError(AppError):
    """Raised when uploaded file does not meet MVP requirements."""


class DatasetNotFoundError(AppError):
    """Raised when a requested dataset ID does not exist."""
