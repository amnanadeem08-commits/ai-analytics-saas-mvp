from __future__ import annotations

"""CORS policy helper (Sprint 8.7)."""

import os
from typing import Sequence


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not raw or raw.strip() == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def cors_allow_credentials() -> bool:
    if "*" in cors_origins():
        return os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() in ("1", "true", "yes")
    return os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() in ("1", "true", "yes")


def cors_methods() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_METHODS", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
    return [m.strip().upper() for m in raw.split(",") if m.strip()]


def cors_headers() -> list[str]:
    raw = os.getenv(
        "CORS_ALLOWED_HEADERS",
        "Authorization,Content-Type,X-CSRF-Token,X-Request-ID,X-API-Key",
    )
    return [h.strip() for h in raw.split(",") if h.strip()]


def validate_cors_config() -> list[str]:
    issues: list[str] = []
    origins = cors_origins()
    if "*" in origins and cors_allow_credentials():
        issues.append("CORS cannot use wildcard origin with credentials enabled")
    return issues
