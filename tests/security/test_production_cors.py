from __future__ import annotations

import pytest

from backend.security.cors_policy import (
    InsecureCorsError,
    assert_production_cors,
    cors_origins,
    validate_cors_config,
)


def test_dev_defaults_to_localhost_when_unset(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    origins = cors_origins()
    assert "http://localhost:8501" in origins
    assert "*" not in origins


def test_dev_allows_explicit_wildcard(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    assert cors_origins() == ["*"]
    assert validate_cors_config() == []
    assert_production_cors()  # no-op outside production


def test_dev_parses_multiple_origins(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:8501, https://preview.example.com",
    )
    assert cors_origins() == [
        "http://localhost:8501",
        "https://preview.example.com",
    ]


def test_production_rejects_missing_origins(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    issues = validate_cors_config()
    assert any("required" in i.lower() for i in issues)
    with pytest.raises(InsecureCorsError):
        assert_production_cors()


def test_production_rejects_wildcard(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(InsecureCorsError):
        assert_production_cors()


def test_production_rejects_wildcard_in_list(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.example.com,*",
    )
    with pytest.raises(InsecureCorsError):
        assert_production_cors()


def test_production_accepts_explicit_origins(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.example.com,https://admin.example.com",
    )
    assert_production_cors()
    assert validate_cors_config() == []
    assert cors_origins() == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_cors_allow_origins_alias(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.example.com")
    assert_production_cors()
    assert cors_origins() == ["https://app.example.com"]
