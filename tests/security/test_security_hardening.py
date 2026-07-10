from __future__ import annotations

import os

from fastapi.testclient import TestClient

from backend.main import app
from backend.security.brute_force import is_locked, record_failure, reset_brute_force_state
from backend.security.dependency_audit import audit_dependencies
from backend.security.rate_limiter import reset_rate_limiter
from backend.security.sanitization import sanitize_string
from backend.security.secrets_validation import validate_secrets
from backend.services.auth_service import reset_auth_store

client = TestClient(app)
STRONG = "Str0ngPass!234567890"


def setup_function():
    reset_auth_store()
    reset_brute_force_state()
    reset_rate_limiter()


def test_security_headers_present():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_input_sanitization_strips_script():
    dirty = "<script>alert(1)</script>hello"
    assert "<script>" not in sanitize_string(dirty)


def test_brute_force_lockout():
    key = "user@x.com:127.0.0.1"
    for _ in range(5):
        record_failure(key)
    assert is_locked(key) is True


def test_failed_login_increments_lockout():
    client.post("/api/v1/auth/register", json={"email": "sec@x.com", "password": STRONG})
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"email": "sec@x.com", "password": "wrong"})
    locked = client.post("/api/v1/auth/login", json={"email": "sec@x.com", "password": STRONG})
    assert locked.status_code == 429


def test_secrets_and_dependency_audit_shapes():
    secrets = validate_secrets()
    assert "issues" in secrets
    deps = audit_dependencies()
    assert deps["package_count"] > 0


def test_release_security_audit_endpoint():
    response = client.get("/api/v1/release/security/audit")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "secrets" in body
    assert "dependencies" in body
