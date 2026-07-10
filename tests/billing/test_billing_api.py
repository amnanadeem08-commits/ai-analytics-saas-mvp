from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.security.security_config import reset_security_config
from backend.services import api_key_service, billing_service, subscription_service, usage_service
from backend.services.auth_service import reset_auth_store

STRONG = "Str0ngPass"
ORG = "org_api_billing"
client = TestClient(app)


def setup_function():
    reset_security_config()
    reset_auth_store()
    usage_service.reset_usage()
    subscription_service.reset_subscriptions()
    billing_service.reset_billing()
    api_key_service.reset_api_keys()


def _auth() -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": "bill@x.com", "password": STRONG})
    token = client.post("/api/v1/auth/login", json={"email": "bill@x.com", "password": STRONG}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_billing_plans_and_subscription_api():
    headers = _auth()
    plans = client.get("/api/v1/billing/plans", headers=headers)
    assert plans.status_code == 200
    assert plans.json()["count"] >= 3

    assigned = client.post(
        f"/api/v1/billing/subscriptions/{ORG}",
        json={"plan_id": "pro", "start_trial": True},
        headers=headers,
    )
    assert assigned.status_code == 201
    sub = client.get(f"/api/v1/billing/subscriptions/{ORG}", headers=headers)
    assert sub.status_code == 200
    assert sub.json()["subscription"]["plan_id"] == "pro"


def test_usage_and_invoice_api():
    headers = _auth()
    client.post(f"/api/v1/billing/subscriptions/{ORG}", json={"plan_id": "free"}, headers=headers)
    usage = client.get(f"/api/v1/billing/usage/{ORG}", headers=headers)
    assert usage.status_code == 200
    invoice = client.post(f"/api/v1/billing/invoices/{ORG}", headers=headers)
    assert invoice.status_code == 201


def test_api_key_api_lifecycle():
    headers = _auth()
    created = client.post(
        "/api/v1/api-keys",
        json={"name": "CI Key", "organization_id": ORG, "scopes": ["read"]},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["secret"].startswith("databot_sk_")
    key_id = created.json()["key"]["key_id"]
    listed = client.get("/api/v1/api-keys", params={"organization_id": ORG}, headers=headers)
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1
    rotated = client.post(f"/api/v1/api-keys/{key_id}/rotate", headers=headers)
    assert rotated.status_code == 200
    revoked = client.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
    assert revoked.status_code == 200
