from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.config.config_loader import load_and_validate, load_raw_config
from backend.config.environment import EnvironmentProfile
from backend.config.validators import ConfigValidationError


@dataclass
class AppSettings:
    """Typed application settings (Sprint 8.5)."""

    app_name: str = "AI Analytics SaaS MVP"
    api_version: str = "1.0.0"
    profile: EnvironmentProfile = EnvironmentProfile.development
    log_level: str = "INFO"
    log_format: str = "json"
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    jwt_secret: str = ""
    jwt_secret_min_length: int = 16
    max_upload_size_mb: int = 200
    queue_backend: str = "memory"
    storage_backend: str = "local"
    database_url: str = "sqlite:///./data/app.db"
    redis_url: str = "redis://127.0.0.1:6379/0"
    worker_enabled: bool = False
    cors_allow_origins: str = "*"
    request_id_header: str = "X-Request-ID"
    correlation_id_header: str = "X-Correlation-ID"
    health_check_timeout_seconds: int = 5
    root_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.profile.is_production

    def public_config(self) -> dict[str, Any]:
        """Redacted config safe for read-only API exposure."""
        return {
            "app_name": self.app_name,
            "api_version": self.api_version,
            "profile": self.profile.value,
            "log_level": self.log_level,
            "log_format": self.log_format,
            "metrics_enabled": self.metrics_enabled,
            "tracing_enabled": self.tracing_enabled,
            "max_upload_size_mb": self.max_upload_size_mb,
            "queue_backend": self.queue_backend,
            "storage_backend": self.storage_backend,
            "database_backend": "sqlite" if self.database_url.startswith("sqlite") else "postgres",
            "worker_enabled": self.worker_enabled,
            "cors_allow_origins": self.cors_allow_origins,
        }


_SETTINGS: AppSettings | None = None


def _from_raw(data: dict[str, Any]) -> AppSettings:
    return AppSettings(
        app_name=str(data.get("APP_NAME", "AI Analytics SaaS MVP")),
        api_version=str(data.get("API_VERSION", "1.0.0")),
        profile=EnvironmentProfile.from_string(str(data.get("APP_ENV", "development"))),
        log_level=str(data.get("LOG_LEVEL", "INFO")).upper(),
        log_format=str(data.get("LOG_FORMAT", "json")).lower(),
        metrics_enabled=bool(data.get("METRICS_ENABLED", True)),
        tracing_enabled=bool(data.get("TRACING_ENABLED", True)),
        jwt_secret=str(data.get("JWT_SECRET", "") or ""),
        jwt_secret_min_length=int(data.get("JWT_SECRET_MIN_LENGTH", 16)),
        max_upload_size_mb=int(data.get("MAX_UPLOAD_SIZE_MB", 200)),
        queue_backend=str(data.get("QUEUE_BACKEND", "memory")).lower(),
        storage_backend=str(data.get("STORAGE_BACKEND", "local")).lower(),
        database_url=str(data.get("DATABASE_URL", "sqlite:///./data/app.db")),
        redis_url=str(data.get("REDIS_URL", "redis://127.0.0.1:6379/0")),
        worker_enabled=bool(data.get("WORKER_ENABLED", False)),
        cors_allow_origins=str(data.get("CORS_ALLOW_ORIGINS", "*")),
        request_id_header=str(data.get("REQUEST_ID_HEADER", "X-Request-ID")),
        correlation_id_header=str(data.get("CORRELATION_ID_HEADER", "X-Correlation-ID")),
        health_check_timeout_seconds=int(data.get("HEALTH_CHECK_TIMEOUT_SECONDS", 5)),
        raw=dict(data),
    )


def get_app_settings(*, refresh: bool = False, validate: bool = False) -> AppSettings:
    global _SETTINGS
    if _SETTINGS is None or refresh:
        data, validation = load_and_validate()
        if validate and not validation["valid"]:
            raise ConfigValidationError("; ".join(validation["issues"]))
        _SETTINGS = _from_raw(data)
    return _SETTINGS


def reset_app_settings() -> None:
    global _SETTINGS
    _SETTINGS = None


def load_settings_from_env(env: dict[str, str] | None = None, *, validate: bool = False) -> AppSettings:
    data = load_raw_config(env=env)  # type: ignore[arg-type]
    if validate:
        validation = __import__("backend.config.validators", fromlist=["validate_settings"]).validate_settings(data)
        if not validation["valid"]:
            raise ConfigValidationError("; ".join(validation["issues"]))
    return _from_raw(data)
