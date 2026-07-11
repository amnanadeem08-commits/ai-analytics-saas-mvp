from __future__ import annotations

"""Secrets validation and production fail-fast (KI-007 / TD-007)."""

import os
from typing import Any

# Development-only fallback used by SecurityConfig when no secret is configured.
DEFAULT_DEV_JWT_SECRET = "dev-insecure-secret-change-me"

_INSECURE_VALUES = frozenset(
    {
        "",
        "changeme",
        "change-me",
        "change-me-in-production-min-16",
        "secret",
        "dev",
        "development",
        "password",
        "test",
        DEFAULT_DEV_JWT_SECRET,
        "local-compose-dev-secret-not-for-production-use",
    }
)

_MIN_PRODUCTION_SECRET_LENGTH = 32


def resolve_jwt_secret() -> str:
    """Resolve JWT signing secret from env (AUTH_JWT_SECRET preferred)."""
    for key in ("AUTH_JWT_SECRET", "JWT_SECRET", "SECRET_KEY"):
        value = (os.getenv(key) or "").strip()
        if value:
            return value
    return DEFAULT_DEV_JWT_SECRET


def _is_production() -> bool:
    profile = (
        os.getenv("ENV_PROFILE")
        or os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or ""
    ).strip().lower()
    return profile in {"production", "prod"}


def _secret_issues(name: str, value: str, *, require_strong: bool) -> list[str]:
    issues: list[str] = []
    stripped = (value or "").strip()
    if not stripped:
        issues.append(f"{name} is not set")
        return issues
    lowered = stripped.lower()
    if lowered in _INSECURE_VALUES or stripped in _INSECURE_VALUES:
        issues.append(f"{name} uses an insecure default/placeholder value")
    if require_strong and len(stripped) < _MIN_PRODUCTION_SECRET_LENGTH:
        issues.append(
            f"{name} must be at least {_MIN_PRODUCTION_SECRET_LENGTH} characters in production"
        )
    elif not require_strong and len(stripped) < 16 and stripped != DEFAULT_DEV_JWT_SECRET:
        issues.append(f"{name} should be at least 16 characters")
    return issues


def validate_secrets() -> dict[str, Any]:
    """Audit JWT-related secrets (used by release/security endpoints)."""
    issues: list[str] = []
    checked: dict[str, str] = {}
    production = _is_production()

    effective = resolve_jwt_secret()
    checked["JWT_EFFECTIVE"] = "set" if effective else "missing"
    issues.extend(_secret_issues("JWT_EFFECTIVE", effective, require_strong=production))

    for key in ("AUTH_JWT_SECRET", "JWT_SECRET", "SECRET_KEY", "DATABASE_URL"):
        value = (os.getenv(key) or "").strip()
        checked[key] = "set" if value else "missing"
        if key == "DATABASE_URL":
            continue
        if value:
            issues.extend(_secret_issues(key, value, require_strong=production))
        elif production and key in {"AUTH_JWT_SECRET", "JWT_SECRET"} and not (
            (os.getenv("AUTH_JWT_SECRET") or "").strip()
            or (os.getenv("JWT_SECRET") or "").strip()
            or (os.getenv("SECRET_KEY") or "").strip()
        ):
            # Only complain once via JWT_EFFECTIVE when none are set.
            pass

    # Deduplicate while preserving order
    deduped: list[str] = []
    seen: set[str] = set()
    for item in issues:
        if item not in seen:
            seen.add(item)
            deduped.append(item)

    return {"checked": checked, "issues": deduped, "ok": len(deduped) == 0}


class InsecureSecretsError(RuntimeError):
    """Raised when production would start with unsafe secrets."""


def assert_production_secrets() -> None:
    """Refuse to boot in production when JWT signing secret is missing or weak.

    Development / test profiles may use the built-in insecure fallback.
    """
    if not _is_production():
        return
    result = validate_secrets()
    if result["ok"]:
        return
    detail = "; ".join(result["issues"])
    raise InsecureSecretsError(
        "Refusing to start in production with insecure secrets. "
        f"{detail}. Set AUTH_JWT_SECRET or JWT_SECRET to a unique value "
        f"(≥{_MIN_PRODUCTION_SECRET_LENGTH} characters)."
    )
