from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.models.user_models import UserRole
from backend.security.security_config import reset_security_config
from backend.services import admin_service, api_key_service, billing_service, subscription_service, usage_service
from backend.services import auth_service

STRONG = "Str0ngPass"
client = TestClient(app)


def setup_function():
    reset_security_config()
    auth_service.reset_auth_store()
    usage_service.reset_usage()
    subscription_service.reset_subscriptions()
    billing_service.reset_billing()
    api_key_service.reset_api_keys()
    admin_service.reset_admin()


def _register_admin() -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": "admin@x.com", "password": STRONG})
    login = client.post("/api/v1/auth/login", json={"email": "admin@x.com", "password": STRONG}).json()
    user_id = login["user"]["user_id"]
    import backend.services.auth_service as auth_mod

    auth_mod._USERS[user_id].role = UserRole.admin
    token = login["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _auth_user() -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": "user@x.com", "password": STRONG})
    token = client.post("/api/v1/auth/login", json={"email": "user@x.com", "password": STRONG}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_requires_admin_role():
    assert client.get("/api/v1/admin/dashboard", headers=_auth_user()).status_code == 403


def test_admin_dashboard():
    headers = _register_admin()
    resp = client.get("/api/v1/admin/dashboard", headers=headers)
    assert resp.status_code == 200
    assert "dashboard" in resp.json()


def test_admin_statistics_and_features():
    headers = _register_admin()
    assert client.get("/api/v1/admin/statistics", headers=headers).status_code == 200
    feats = client.get("/api/v1/admin/features", headers=headers)
    assert feats.status_code == 200
    toggled = client.put("/api/v1/admin/features/test_feature", json={"enabled": False}, headers=headers)
    assert toggled.status_code == 200
    assert toggled.json()["features"]["test_feature"] is False
