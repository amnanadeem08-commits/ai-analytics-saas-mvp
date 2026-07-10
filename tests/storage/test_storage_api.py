from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.security.security_config import reset_security_config
from backend.services.auth_service import reset_auth_store
from backend.services import storage_service

STRONG = "Str0ngPass"
client = TestClient(app)


def setup_function():
    reset_security_config()
    reset_auth_store()
    storage_service.reset_storage()


def _auth() -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": "storage@x.com", "password": STRONG})
    token = client.post("/api/v1/auth/login", json={"email": "storage@x.com", "password": STRONG}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_storage_endpoints_require_auth():
    assert client.get("/api/v1/storage/files").status_code == 401


def test_upload_list_get_download_statistics():
    headers = _auth()
    uploaded = client.post(
        "/api/v1/storage/upload",
        headers=headers,
        params={"artifact_type": "temporary_upload"},
        files={"file": ("note.txt", b"hello storage", "text/plain")},
    )
    assert uploaded.status_code == 201
    obj = uploaded.json()["object"]
    object_id = obj["object_id"]

    got = client.get(f"/api/v1/storage/{object_id}", headers=headers)
    assert got.status_code == 200

    listing = client.get("/api/v1/storage/files", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["count"] >= 1

    download = client.get(f"/api/v1/storage/{object_id}/download", headers=headers)
    assert download.status_code == 200
    assert download.json()["size_bytes"] == len(b"hello storage")

    stats = client.get("/api/v1/storage/statistics", headers=headers)
    assert stats.status_code == 200
    assert stats.json()["statistics"]["total_objects"] >= 1


def test_archive_restore_delete():
    headers = _auth()
    uploaded = client.post(
        "/api/v1/storage/upload",
        headers=headers,
        files={"file": ("x.bin", b"x", "application/octet-stream")},
    )
    object_id = uploaded.json()["object"]["object_id"]
    assert client.post(f"/api/v1/storage/{object_id}/archive", headers=headers).status_code == 200
    assert client.post(f"/api/v1/storage/{object_id}/restore", headers=headers).status_code == 200
    assert client.delete(f"/api/v1/storage/{object_id}", headers=headers).status_code == 200


def test_openapi_includes_storage_routes():
    schema = client.get("/openapi.json").json()
    paths = schema.get("paths") or {}
    assert "/api/v1/storage/upload" in paths
    assert "/api/v1/storage/statistics" in paths
