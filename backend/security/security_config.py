from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Development-only fallback secret. Production MUST set AUTH_JWT_SECRET.
_DEFAULT_DEV_SECRET = "dev-insecure-secret-change-me"


@dataclass
class SecurityConfig:
    """Environment-driven security configuration.

    Never hardcodes production secrets. All values are overridable via env vars.
    """

    jwt_secret: str = field(default_factory=lambda: os.getenv("AUTH_JWT_SECRET", _DEFAULT_DEV_SECRET))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("AUTH_JWT_ALGORITHM", "HS256"))
    jwt_issuer: str = field(default_factory=lambda: os.getenv("AUTH_JWT_ISSUER", "ai-analytics-saas"))
    jwt_audience: str = field(default_factory=lambda: os.getenv("AUTH_JWT_AUDIENCE", "ai-analytics-clients"))

    access_token_ttl_seconds: int = field(
        default_factory=lambda: _int_env("AUTH_ACCESS_TTL_SECONDS", 900)  # 15 min
    )
    refresh_token_ttl_seconds: int = field(
        default_factory=lambda: _int_env("AUTH_REFRESH_TTL_SECONDS", 60 * 60 * 24 * 14)  # 14 days
    )
    email_verification_ttl_seconds: int = field(
        default_factory=lambda: _int_env("AUTH_EMAIL_VERIFY_TTL_SECONDS", 60 * 60 * 24)  # 24 h
    )
    password_reset_ttl_seconds: int = field(
        default_factory=lambda: _int_env("AUTH_PASSWORD_RESET_TTL_SECONDS", 60 * 60)  # 1 h
    )

    # Password policy
    password_min_length: int = field(default_factory=lambda: _int_env("AUTH_PASSWORD_MIN_LENGTH", 8))
    password_require_upper: bool = field(default_factory=lambda: _bool_env("AUTH_PASSWORD_REQUIRE_UPPER", True))
    password_require_lower: bool = field(default_factory=lambda: _bool_env("AUTH_PASSWORD_REQUIRE_LOWER", True))
    password_require_digit: bool = field(default_factory=lambda: _bool_env("AUTH_PASSWORD_REQUIRE_DIGIT", True))
    password_require_symbol: bool = field(default_factory=lambda: _bool_env("AUTH_PASSWORD_REQUIRE_SYMBOL", False))

    # PBKDF2 hashing
    pbkdf2_iterations: int = field(default_factory=lambda: _int_env("AUTH_PBKDF2_ITERATIONS", 240_000))

    # Session / concurrency
    max_concurrent_sessions: int = field(default_factory=lambda: _int_env("AUTH_MAX_CONCURRENT_SESSIONS", 5))

    # Cookie / CSRF (optional; disabled by default for the token-header flow)
    secure_cookies: bool = field(default_factory=lambda: _bool_env("AUTH_SECURE_COOKIES", False))
    cookie_domain: str = field(default_factory=lambda: os.getenv("AUTH_COOKIE_DOMAIN", ""))
    csrf_protection: bool = field(default_factory=lambda: _bool_env("AUTH_CSRF_PROTECTION", False))

    @property
    def using_dev_secret(self) -> bool:
        return self.jwt_secret == _DEFAULT_DEV_SECRET


_CONFIG: SecurityConfig | None = None


def get_security_config(*, refresh: bool = False) -> SecurityConfig:
    """Return the process-wide security config (rebuilds when refresh=True)."""
    global _CONFIG
    if _CONFIG is None or refresh:
        _CONFIG = SecurityConfig()
    return _CONFIG


def reset_security_config() -> None:
    """Test helper — force reload from the current environment on next access."""
    global _CONFIG
    _CONFIG = None
