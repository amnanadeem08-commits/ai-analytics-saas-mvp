from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.security.security_config import reset_security_config
from backend.services import job_service
from backend.services.auth_service import reset_auth_store

STRONG = "Str0ngPass"
client = TestClient(app)


def setup_function():
    reset_security_config()
    reset_auth_store()
    job_service.reset_jobs()


def _auth() -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": "jobs@x.com", "password": STRONG})
    token = client.post("/api/v1/auth/login", json={"email": "jobs@x.com", "password": STRONG}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_jobs_endpoints_require_auth():
    assert client.post("/api/v1/jobs", json={"job_type": "generic"}).status_code == 401


def test_submit_get_list_statistics():
    headers = _auth()
    submitted = client.post(
        "/api/v1/jobs",
        json={"job_type": "generic", "payload": {"echo": "hi", "steps": 2}, "inline": True},
        headers=headers,
    )
    assert submitted.status_code == 201
    job = submitted.json()["job"]
    assert job["status"] == "succeeded"
    job_id = job["job_id"]

    got = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["job"]["job_id"] == job_id

    listed = client.get("/api/v1/jobs", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1

    stats = client.get("/api/v1/jobs/statistics", headers=headers)
    assert stats.status_code == 200
    assert stats.json()["statistics"]["total_jobs"] >= 1


def test_cancel_and_retry_via_api():
    headers = _auth()
    # Queue (not inline) so it can be cancelled.
    submitted = client.post(
        "/api/v1/jobs",
        json={"job_type": "generic", "payload": {"echo": "x"}, "inline": False},
        headers=headers,
    )
    job_id = submitted.json()["job"]["job_id"]
    cancelled = client.delete(f"/api/v1/jobs/{job_id}", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["job"]["status"] == "cancelled"

    retried = client.post(f"/api/v1/jobs/{job_id}/retry", params={"inline": True}, headers=headers)
    assert retried.status_code == 200
    assert retried.json()["job"]["status"] == "succeeded"


def test_missing_job_404():
    headers = _auth()
    assert client.get("/api/v1/jobs/missing", headers=headers).status_code == 404


def test_openapi_includes_job_routes():
    schema = client.get("/openapi.json").json()
    paths = schema.get("paths") or {}
    assert "/api/v1/jobs" in paths
    assert "/api/v1/jobs/{job_id}" in paths
    assert "/api/v1/jobs/statistics" in paths
