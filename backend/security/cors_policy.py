from __future__ import annotations

"""CORS policy helper (Sprint 8.7) + production fail-fast (KI-006 / TD-006)."""

import os
from typing import Sequence

# Development-only defaults when CORS_ALLOWED_ORIGINS is unset.
_DEV_LOCALHOST_ORIGINS: tuple[str, ...] = (
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
)


class InsecureCorsError(RuntimeError):
    """Raised when production would start with unsafe CORS configuration."""


def _is_production() -> bool:
    profile = (
        os.getenv("ENV_PROFILE")
        or os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or ""
    ).strip().lower()
    return profile in {"production", "prod"}


def _raw_origins_env() -> str:
    return (os.getenv("CORS_ALLOWED_ORIGINS") or os.getenv("CORS_ALLOW_ORIGINS") or "").strip()


def _parse_origins(raw: str) -> list[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]


def cors_origins() -> list[str]:
    """Resolve allowed origins.

    - Production: only explicit non-wildcard origins from env (may be empty → fail-fast).
    - Development: explicit env wins; ``*`` allowed; unset → localhost defaults.
      Set ``CORS_ALLOWED_ORIGINS=*`` to restore fully open local CORS.
    """
    raw = _raw_origins_env()
    if raw:
        if raw == "*":
            return ["*"]
        return _parse_origins(raw)
    if _is_production():
        return []
    return list(_DEV_LOCALHOST_ORIGINS)


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
    """Return CORS configuration issues (used by audits + production fail-fast)."""
    issues: list[str] = []
    raw = _raw_origins_env()
    origins = cors_origins()

    if _is_production():
        if not raw:
            issues.append(
                "CORS_ALLOWED_ORIGINS is required in production "
                "(comma-separated explicit origins; wildcard * is not allowed)"
            )
        elif "*" in _parse_origins(raw) or raw.strip() == "*":
            issues.append("CORS_ALLOWED_ORIGINS must not use wildcard (*) in production")
        elif not origins:
            issues.append("CORS_ALLOWED_ORIGINS resolved to an empty origin list")
        else:
            for origin in origins:
                if origin == "*":
                    issues.append("CORS_ALLOWED_ORIGINS must not include wildcard (*)")
                elif not (
                    origin.startswith("http://")
                    or origin.startswith("https://")
                ):
                    issues.append(f"CORS origin must be an absolute http(s) URL: {origin}")

    if "*" in origins and os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() in (
        "1",
        "true",
        "yes",
    ):
        issues.append("CORS cannot use wildcard origin with credentials enabled")

    # Deduplicate
    seen: set[str] = set()
    ordered: list[str] = []
    for item in issues:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def assert_production_cors() -> None:
    """Refuse to boot in production with missing or wildcard CORS origins."""
    if not _is_production():
        return
    issues = validate_cors_config()
    if not issues:
        return
    detail = "; ".join(issues)
    raise InsecureCorsError(
        "Refusing to start in production with insecure CORS configuration. "
        f"{detail}. Set CORS_ALLOWED_ORIGINS to an explicit comma-separated list, "
        "e.g. https://app.example.com,https://admin.example.com."
    )
