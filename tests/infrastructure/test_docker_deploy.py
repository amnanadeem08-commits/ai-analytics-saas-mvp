from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCKER = ROOT / "docker"
DEPLOY = ROOT / "deploy"


def test_docker_files_exist():
    assert (DOCKER / "docker-compose.yml").exists()
    assert (DOCKER / "Dockerfile.backend").exists()
    assert (DOCKER / "Dockerfile.frontend").exists()
    assert (DOCKER / "Dockerfile.worker").exists()
    assert (DOCKER / ".env.example").exists()
    assert (DOCKER / ".env.production.example").exists()
    assert (DOCKER / "verify_prod_compose.py").exists()


def test_compose_defines_core_services():
    text = (DOCKER / "docker-compose.yml").read_text(encoding="utf-8")
    for service in ("postgres", "redis", "backend", "frontend", "worker"):
        assert service in text
    assert "api/v1/live" in text
    assert "condition: service_healthy" in text


def test_deploy_scripts_exist():
    for name in ("start.sh", "stop.sh", "restart.sh", "health_check.sh", "backup.sh", "restore.sh"):
        assert (DEPLOY / name).exists(), f"Missing deploy/{name}"


def test_env_example_documents_key_vars():
    env = (DOCKER / ".env.example").read_text(encoding="utf-8")
    for key in ("APP_ENV", "JWT_SECRET", "DATABASE_URL", "REDIS_URL", "LOG_FORMAT"):
        assert key in env


def test_production_env_example_is_hardened():
    env = (DOCKER / ".env.production.example").read_text(encoding="utf-8")
    assert "APP_ENV=production" in env
    assert "AUTH_JWT_SECRET=" in env
    assert "CORS_ALLOWED_ORIGINS=" in env
    assert "CORS_ALLOWED_ORIGINS=*" not in env.replace(" ", "")
    assert "STORAGE_METADATA_BACKEND=sqlalchemy" in env


def test_verify_prod_compose_script_static():
    import runpy

    script = DOCKER / "verify_prod_compose.py"
    ns = runpy.run_path(str(script))
    code = ns["main"]([])
    assert code == 0
