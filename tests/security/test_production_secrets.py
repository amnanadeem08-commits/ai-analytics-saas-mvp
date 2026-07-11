from __future__ import annotations

import pytest

from backend.security.secrets_validation import (
    DEFAULT_DEV_JWT_SECRET,
    InsecureSecretsError,
    assert_production_secrets,
    resolve_jwt_secret,
    validate_secrets,
)
from backend.security.security_config import get_security_config, reset_security_config


def test_resolve_prefers_auth_jwt_secret(monkeypatch):
    monkeypatch.setenv("AUTH_JWT_SECRET", "auth-secret-value-at-least-32-chars!!")
    monkeypatch.setenv("JWT_SECRET", "other-secret-value-at-least-32-chars!!")
    assert resolve_jwt_secret() == "auth-secret-value-at-least-32-chars!!"


def test_resolve_falls_back_to_jwt_secret(monkeypatch):
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    monkeypatch.setenv("JWT_SECRET", "jwt-secret-value-at-least-32-chars!!!")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    assert resolve_jwt_secret() == "jwt-secret-value-at-least-32-chars!!!"


def test_resolve_uses_dev_default_when_unset(monkeypatch):
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    assert resolve_jwt_secret() == DEFAULT_DEV_JWT_SECRET


def test_validate_secrets_flags_dev_default(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    result = validate_secrets()
    assert result["ok"] is False
    assert any("insecure" in issue.lower() for issue in result["issues"])


def test_assert_production_secrets_rejects_missing(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(InsecureSecretsError):
        assert_production_secrets()


def test_assert_production_secrets_rejects_short_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "short-but-not-placeholder")
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    with pytest.raises(InsecureSecretsError):
        assert_production_secrets()


def test_assert_production_secrets_rejects_placeholder(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "change-me-in-production-min-16")
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    with pytest.raises(InsecureSecretsError):
        assert_production_secrets()


def test_assert_production_secrets_accepts_strong_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "AUTH_JWT_SECRET",
        "production-grade-signing-secret-32chars-min-ok",
    )
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    assert_production_secrets()  # does not raise
    result = validate_secrets()
    assert result["ok"] is True


def test_assert_skipped_outside_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    assert_production_secrets()  # does not raise


def test_security_config_uses_resolved_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "resolved-from-jwt-secret-32chars-min")
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    reset_security_config()
    cfg = get_security_config(refresh=True)
    assert cfg.jwt_secret == "resolved-from-jwt-secret-32chars-min"
    reset_security_config()
