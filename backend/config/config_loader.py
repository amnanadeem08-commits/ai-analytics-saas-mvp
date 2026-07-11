from __future__ import annotations

import os
from typing import Any

from backend.config.defaults import DEFAULTS
from backend.config.environment import EnvironmentProfile
from backend.config.validators import validate_settings


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _profile_overrides(profile: EnvironmentProfile) -> dict[str, object]:
    if profile is EnvironmentProfile.testing:
        return {
            "LOG_LEVEL": "WARNING",
            "METRICS_ENABLED": True,
            "TRACING_ENABLED": False,
            "WORKER_ENABLED": False,
        }
    if profile is EnvironmentProfile.production:
        return {
            "LOG_LEVEL": "INFO",
            "LOG_FORMAT": "json",
            "METRICS_ENABLED": True,
            "TRACING_ENABLED": True,
        }
    return {
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "text",
        "METRICS_ENABLED": True,
        "TRACING_ENABLED": True,
    }


def load_raw_config(*, env: os._Environ[str] | None = None) -> dict[str, Any]:
    """Merge defaults, profile overrides, and environment variables."""
    source = env or os.environ
    profile = EnvironmentProfile.from_string(source.get("APP_ENV", str(DEFAULTS["APP_ENV"])))
    merged: dict[str, Any] = dict(DEFAULTS)
    merged.update(_profile_overrides(profile))
    merged["APP_ENV"] = profile.value

    env_map = {
        "APP_NAME": "APP_NAME",
        "API_VERSION": "API_VERSION",
        "APP_ENV": "APP_ENV",
        "LOG_LEVEL": "LOG_LEVEL",
        "LOG_FORMAT": "LOG_FORMAT",
        "METRICS_ENABLED": "METRICS_ENABLED",
        "TRACING_ENABLED": "TRACING_ENABLED",
        "JWT_SECRET": "JWT_SECRET",
        "AUTH_JWT_SECRET": "AUTH_JWT_SECRET",
        "SECRET_KEY": "SECRET_KEY",
        "JWT_SECRET_MIN_LENGTH": "JWT_SECRET_MIN_LENGTH",
        "MAX_UPLOAD_SIZE_MB": "MAX_UPLOAD_SIZE_MB",
        "QUEUE_BACKEND": "QUEUE_BACKEND",
        "STORAGE_BACKEND": "STORAGE_BACKEND",
        "DATABASE_URL": "DATABASE_URL",
        "STORAGE_BACKEND_DB": "STORAGE_BACKEND",
        "REDIS_URL": "REDIS_URL",
        "WORKER_ENABLED": "WORKER_ENABLED",
        "CORS_ALLOW_ORIGINS": "CORS_ALLOW_ORIGINS",
    }
    for key, env_key in env_map.items():
        if env_key in source and source[env_key] != "":
            merged[key] = source[env_key]

    for bool_key in ("METRICS_ENABLED", "TRACING_ENABLED", "WORKER_ENABLED"):
        merged[bool_key] = _coerce_bool(merged.get(bool_key))

    if "JWT_SECRET" not in merged or not merged["JWT_SECRET"]:
        merged["JWT_SECRET"] = merged.get("AUTH_JWT_SECRET") or merged.get("SECRET_KEY", "")
    if "AUTH_JWT_SECRET" in merged and merged["AUTH_JWT_SECRET"] and not merged.get("JWT_SECRET"):
        merged["JWT_SECRET"] = merged["AUTH_JWT_SECRET"]

    try:
        merged["MAX_UPLOAD_SIZE_MB"] = int(merged.get("MAX_UPLOAD_SIZE_MB", 200))
    except (TypeError, ValueError):
        merged["MAX_UPLOAD_SIZE_MB"] = 200

    try:
        merged["JWT_SECRET_MIN_LENGTH"] = int(merged.get("JWT_SECRET_MIN_LENGTH", 16))
    except (TypeError, ValueError):
        merged["JWT_SECRET_MIN_LENGTH"] = 16

    return merged


def load_and_validate(*, env: os._Environ[str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    data = load_raw_config(env=env)
    validation = validate_settings(data)
    return data, validation
