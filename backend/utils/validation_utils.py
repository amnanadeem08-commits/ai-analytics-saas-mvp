from backend.core.config import settings
from backend.core.exceptions import FileValidationError
from backend.utils.file_utils import file_extension


def validate_tabular_upload(filename: str, content: bytes) -> None:
    """Validate supported tabular uploads before saving to local storage."""
    if not filename:
        raise FileValidationError("Missing filename.")

    if file_extension(filename) not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise FileValidationError(f"Only {allowed} files are supported.")

    if not content:
        raise FileValidationError("Uploaded file is empty.")

    if len(content) > settings.max_upload_size_bytes:
        raise FileValidationError(
            f"File is too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB."
        )


def validate_csv_upload(filename: str, content: bytes) -> None:
    """Backward-compatible alias for older callers."""
    validate_tabular_upload(filename, content)
