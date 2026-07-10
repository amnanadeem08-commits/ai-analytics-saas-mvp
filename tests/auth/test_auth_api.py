from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.security.security_config import reset_security_config
from backend.services.auth_service import reset_auth_store

STRONG = "Str0ngPass"

client = TestClient(app)


def setup_function():
    reset_security_config()
    reset_auth_store()


def _register(email="api@example.com", password=STRONG):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "API User"},
    )


def test_register_endpoint():
    resp = _register()
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["user"]["email"] == "api@example.com"
    assert "hashed_password" not in body["user"]


def test_register_weak_password_422():
    resp = client.post("/api/v1/auth/register", json={"email": "x@y.com", "password": "weak"})
    assert resp.status_code == 422
    assert resp.json()["success"] is False


def test_login_and_me():
    _register()
    login = client.post("/api/v1/auth/login", json={"email": "api@example.com", "password": STRONG})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "api@example.com"


def test_protected_endpoint_requires_auth():
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["success"] is False


def test_invalid_token_rejected():
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401


def test_login_invalid_credentials():
    _register()
    resp = client.post("/api/v1/auth/login", json={"email": "api@example.com", "password": "WrongPass1"})
    assert resp.status_code == 401


def test_refresh_endpoint():
    _register()
    login = client.post("/api/v1/auth/login", json={"email": "api@example.com", "password": STRONG})
    refresh_token = login.json()["refresh_token"]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_logout_endpoint():
    _register()
    login = client.post("/api/v1/auth/login", json={"email": "api@example.com", "password": STRONG})
    token = login.json()["access_token"]
    session_id = login.json()["session_id"]
    resp = client.post(
        "/api/v1/auth/logout",
        json={"session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    # Session revoked → token no longer valid
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 401


def test_change_password_endpoint():
    _register()
    login = client.post("/api/v1/auth/login", json={"email": "api@example.com", "password": STRONG})
    token = login.json()["access_token"]
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": STRONG, "new_password": "NewStr0ngPass"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    relogin = client.post(
        "/api/v1/auth/login", json={"email": "api@example.com", "password": "NewStr0ngPass"}
    )
    assert relogin.status_code == 200


def test_password_reset_endpoints():
    _register()
    req = client.post("/api/v1/auth/request-password-reset", json={"email": "api@example.com"})
    assert req.status_code == 200
    reset_token = req.json()["verification_token"]
    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "ResetStr0ng1"},
    )
    assert resp.status_code == 200


def test_openapi_includes_auth_routes():
    schema = client.get("/openapi.json").json()
    paths = schema.get("paths") or {}
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/auth/refresh" in paths


def test_existing_ai_routes_still_public():
    # AI functionality must keep working without authentication.
    caps = client.get("/api/v1/capabilities")
    assert caps.status_code == 200
    assert "authentication" in caps.json()["capabilities"]
    health = client.get("/api/v1/health")
    assert health.status_code == 200
