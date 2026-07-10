from __future__ import annotations

"""Default configuration values (Sprint 8.5)."""

DEFAULTS: dict[str, object] = {
    "APP_NAME": "AI Analytics SaaS MVP",
    "API_VERSION": "1.0.0",
    "APP_ENV": "development",
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "json",
    "METRICS_ENABLED": True,
    "TRACING_ENABLED": True,
    "HEALTH_CHECK_TIMEOUT_SECONDS": 5,
    "JWT_SECRET_MIN_LENGTH": 16,
    "MAX_UPLOAD_SIZE_MB": 200,
    "QUEUE_BACKEND": "memory",
    "STORAGE_BACKEND": "local",
    "DATABASE_URL": "sqlite:///./data/app.db",
    "STORAGE_BACKEND_DB": "memory",
    "REDIS_URL": "redis://127.0.0.1:6379/0",
    "WORKER_ENABLED": False,
    "CORS_ALLOW_ORIGINS": "*",
    "REQUEST_ID_HEADER": "X-Request-ID",
    "CORRELATION_ID_HEADER": "X-Correlation-ID",
}
