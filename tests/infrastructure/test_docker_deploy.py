from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCKER = ROOT / "docker"
DEPLOY = ROOT / "deploy"


def test_docker_files_exist():
    assert (DOCKER / "docker-compose.yml").exists()
    assert (DOCKER / "Dockerfile.backend").exists()
    assert (DOCKER / "Dockerfile.frontend").exists()
    assert (DOCKER / "Dockerfile.worker").exists()
    assert (DOCKER / ".env.example").exists()


def test_compose_defines_core_services():
    text = (DOCKER / "docker-compose.yml").read_text(encoding="utf-8")
    for service in ("postgres", "redis", "backend", "frontend", "worker"):
        assert service in text


def test_deploy_scripts_exist():
    for name in ("start.sh", "stop.sh", "restart.sh", "health_check.sh", "backup.sh", "restore.sh"):
        assert (DEPLOY / name).exists(), f"Missing deploy/{name}"


def test_env_example_documents_key_vars():
    env = (DOCKER / ".env.example").read_text(encoding="utf-8")
    for key in ("APP_ENV", "JWT_SECRET", "DATABASE_URL", "REDIS_URL", "LOG_FORMAT"):
        assert key in env
