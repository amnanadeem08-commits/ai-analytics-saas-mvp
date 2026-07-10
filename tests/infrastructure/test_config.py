from __future__ import annotations

import os

import pytest

from backend.config.config_loader import load_and_validate, load_raw_config
from backend.config.environment import EnvironmentProfile
from backend.config.settings import get_app_settings, load_settings_from_env, reset_app_settings
from backend.config.validators import validate_settings


def setup_function():
    reset_app_settings()


def test_environment_profiles():
    assert EnvironmentProfile.from_string("production").is_production
    assert EnvironmentProfile.from_string("testing").is_testing
    assert EnvironmentProfile.from_string("development").is_development


def test_load_raw_config_defaults():
    data = load_raw_config(env={})
    assert data["APP_ENV"] == "development"
    assert data["QUEUE_BACKEND"] == "memory"


def test_production_validation_requires_secret():
    env = {
        "APP_ENV": "production",
        "JWT_SECRET": "short",
        "LOG_FORMAT": "text",
        "DATABASE_URL": "sqlite:///./data/app.db",
    }
    validation = validate_settings(load_raw_config(env=env))
    assert validation["valid"] is False
    assert any("JWT_SECRET" in issue for issue in validation["issues"])


def test_testing_profile_overrides():
    env = {"APP_ENV": "testing"}
    data = load_raw_config(env=env)
    assert data["LOG_LEVEL"] == "WARNING"


def test_get_app_settings_public_config_redacts_secrets():
    settings = load_settings_from_env({"APP_ENV": "development", "JWT_SECRET": "dev-secret-1234567890"})
    public = settings.public_config()
    assert "jwt_secret" not in public
    assert public["profile"] == "development"


def test_load_and_validate_returns_tuple():
    data, validation = load_and_validate()
    assert "APP_NAME" in data
    assert "valid" in validation
