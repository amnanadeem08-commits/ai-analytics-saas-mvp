from __future__ import annotations

from typing import Any

from backend.config.environment import EnvironmentProfile


class ConfigValidationError(ValueError):
    pass


def validate_secret(name: str, value: str, *, min_length: int = 16, required_in_production: bool = True) -> list[str]:
    issues: list[str] = []
    if not value or not str(value).strip():
        if required_in_production:
            issues.append(f"{name} is required")
        return issues
    if len(value) < min_length:
        issues.append(f"{name} must be at least {min_length} characters")
    lowered = value.lower()
    if lowered in {
        "changeme",
        "change-me",
        "change-me-in-production-min-16",
        "secret",
        "password",
        "test",
        "dev",
        "development",
        "dev-insecure-secret-change-me",
        "local-compose-dev-secret-not-for-production-use",
    }:
        issues.append(f"{name} must not use a placeholder value")
    return issues


def validate_settings(data: dict[str, Any]) -> dict[str, Any]:
    """Validate resolved settings; returns {valid, issues}."""
    issues: list[str] = []
    profile = EnvironmentProfile.from_string(str(data.get("APP_ENV", "development")))

    if not str(data.get("APP_NAME", "")).strip():
        issues.append("APP_NAME is required")

    log_level = str(data.get("LOG_LEVEL", "INFO")).upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        issues.append(f"Invalid LOG_LEVEL: {log_level}")

    max_upload = data.get("MAX_UPLOAD_SIZE_MB", 200)
    try:
        if int(max_upload) <= 0:
            issues.append("MAX_UPLOAD_SIZE_MB must be positive")
    except (TypeError, ValueError):
        issues.append("MAX_UPLOAD_SIZE_MB must be an integer")

    jwt_secret = str(
        data.get("AUTH_JWT_SECRET", "")
        or data.get("JWT_SECRET", "")
        or data.get("SECRET_KEY", "")
        or ""
    )
    min_len = int(data.get("JWT_SECRET_MIN_LENGTH", 32 if profile.is_production else 16))
    if profile.is_production:
        issues.extend(validate_secret("JWT_SECRET", jwt_secret, min_length=min_len))
        if str(data.get("LOG_FORMAT", "")).lower() != "json":
            issues.append("LOG_FORMAT should be 'json' in production")
    elif jwt_secret:
        issues.extend(validate_secret("JWT_SECRET", jwt_secret, min_length=min_len, required_in_production=False))

    queue_backend = str(data.get("QUEUE_BACKEND", "memory")).lower()
    if queue_backend not in {"memory", "redis"}:
        issues.append(f"Unsupported QUEUE_BACKEND: {queue_backend}")

    storage_backend = str(data.get("STORAGE_BACKEND", "local")).lower()
    if storage_backend not in {"local", "s3", "aws"}:
        issues.append(f"Unsupported STORAGE_BACKEND: {storage_backend}")

    db_url = str(data.get("DATABASE_URL", ""))
    if profile.is_production and db_url.startswith("sqlite:"):
        issues.append("Production should not use SQLite DATABASE_URL")

    return {"valid": not issues, "issues": issues, "profile": profile.value}
