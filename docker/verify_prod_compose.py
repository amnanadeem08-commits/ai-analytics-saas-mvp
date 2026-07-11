#!/usr/bin/env python3
"""Verify Docker Compose production readiness (static + optional live probes).

Static checks always run (no Docker required).
Live checks require the Docker CLI and a running prod stack:

    cd docker
    copy .env.production.example .env.production   # then set real secrets
    docker compose --env-file .env.production --profile prod up --build -d
    python verify_prod_compose.py --live
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

DOCKER_DIR = Path(__file__).resolve().parent
ROOT = DOCKER_DIR.parent

REQUIRED_FILES = (
    "docker-compose.yml",
    "Dockerfile.backend",
    "Dockerfile.frontend",
    "Dockerfile.worker",
    ".env.example",
    ".env.production.example",
)

REQUIRED_SERVICES = ("postgres", "redis", "backend", "frontend", "worker")
REQUIRED_PROD_ENV_KEYS = (
    "APP_ENV",
    "AUTH_JWT_SECRET",
    "JWT_SECRET",
    "CORS_ALLOWED_ORIGINS",
    "DATABASE_URL",
    "REDIS_URL",
    "STORAGE_BACKEND",
)


def _ok(msg: str) -> None:
    print(f"PASS  {msg}")


def _fail(msg: str, errors: list[str]) -> None:
    print(f"FAIL  {msg}")
    errors.append(msg)


def check_files(errors: list[str]) -> None:
    for name in REQUIRED_FILES:
        path = DOCKER_DIR / name
        if path.exists():
            _ok(f"file exists: {name}")
        else:
            _fail(f"missing file: {name}", errors)


def check_compose_services(errors: list[str]) -> None:
    text = (DOCKER_DIR / "docker-compose.yml").read_text(encoding="utf-8")
    for service in REQUIRED_SERVICES:
        if f"{service}:" in text or f"  {service}:" in text:
            _ok(f"compose service present: {service}")
        else:
            _fail(f"compose missing service: {service}", errors)
    if "profiles: [prod]" in text or "profiles: [dev, prod]" in text:
        _ok("compose defines prod profile")
    else:
        _fail("compose missing prod profile markers", errors)
    if "api/v1/live" in text:
        _ok("backend healthcheck probes /api/v1/live")
    else:
        _fail("backend compose healthcheck missing /api/v1/live", errors)


def check_production_env_template(errors: list[str]) -> None:
    env = (DOCKER_DIR / ".env.production.example").read_text(encoding="utf-8")
    for key in REQUIRED_PROD_ENV_KEYS:
        if key in env:
            _ok(f"production env documents {key}")
        else:
            _fail(f"production env missing {key}", errors)
    if "APP_ENV=production" not in env:
        _fail("production env must set APP_ENV=production", errors)
    else:
        _ok("production env sets APP_ENV=production")
    if "CORS_ALLOWED_ORIGINS=*" in env.replace(" ", ""):
        _fail("production env must not use CORS wildcard *", errors)
    else:
        _ok("production env avoids CORS wildcard")
    if "REPLACE_WITH_TOKEN" in env or "AUTH_JWT_SECRET=" in env:
        _ok("production env requires operator-supplied JWT secret")


def check_dockerfiles(errors: list[str]) -> None:
    backend = (DOCKER_DIR / "Dockerfile.backend").read_text(encoding="utf-8")
    if "api/v1/live" in backend:
        _ok("Dockerfile.backend HEALTHCHECK uses /api/v1/live")
    else:
        _fail("Dockerfile.backend missing liveness healthcheck", errors)
    worker = (DOCKER_DIR / "Dockerfile.worker").read_text(encoding="utf-8")
    if "backend.workers" in worker:
        _ok("Dockerfile.worker starts worker CLI")
    else:
        _fail("Dockerfile.worker missing worker entrypoint", errors)


def check_failfast_contract(errors: list[str]) -> None:
    """Ensure production fail-fast helpers still exist (KI-006 / KI-007)."""
    secrets = ROOT / "backend" / "security" / "secrets_validation.py"
    cors = ROOT / "backend" / "security" / "cors_policy.py"
    main = ROOT / "backend" / "main.py"
    for path, needle in (
        (secrets, "assert_production_secrets"),
        (cors, "assert_production_cors"),
        (main, "assert_production_cors"),
        (main, "assert_production_secrets"),
    ):
        text = path.read_text(encoding="utf-8")
        if needle in text:
            _ok(f"{path.name} includes {needle}")
        else:
            _fail(f"{path.name} missing {needle}", errors)


def check_live(errors: list[str], *, base_url: str) -> None:
    docker = shutil.which("docker")
    if not docker:
        _fail("Docker CLI not found on PATH — install Docker Desktop to run --live", errors)
        return
    _ok(f"Docker CLI found: {docker}")
    for path in ("/api/v1/live", "/api/v1/ready", "/health"):
        url = base_url.rstrip("/") + path
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                if 200 <= resp.status < 300:
                    _ok(f"live probe {path} → HTTP {resp.status}")
                else:
                    _fail(f"live probe {path} → HTTP {resp.status}", errors)
        except urllib.error.URLError as exc:
            _fail(f"live probe {path} failed: {exc}", errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Probe a running stack (requires Docker + compose up)",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("VERIFY_BASE_URL", "http://127.0.0.1:8000"),
        help="API base URL for --live probes",
    )
    args = parser.parse_args(argv)

    print("=== Docker Compose production verification ===")
    print(f"docker dir: {DOCKER_DIR}")
    errors: list[str] = []
    check_files(errors)
    check_compose_services(errors)
    check_production_env_template(errors)
    check_dockerfiles(errors)
    check_failfast_contract(errors)
    if args.live:
        check_live(errors, base_url=args.base_url)
    else:
        print("SKIP  live probes (pass --live when the prod stack is up)")

    print("=== Summary ===")
    if errors:
        print(f"FAILED ({len(errors)} issue(s))")
        for item in errors:
            print(f"  - {item}")
        return 1
    print("PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
