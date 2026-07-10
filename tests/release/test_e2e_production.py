from __future__ import annotations

"""End-to-end production validation using the real sample sales dataset."""

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.core.config import ensure_data_directories, settings
from backend.core.theme_manager import theme_manager
from backend.main import app
from backend.security.rate_limiter import reset_rate_limiter
from backend.services.auth_service import reset_auth_store

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "samples" / "sample_sales_data.csv"
STRONG = "Str0ngPass!234567890"


def setup_function():
    reset_auth_store()
    reset_rate_limiter()


def test_e2e_real_dataset_upload_analytics_and_release_gates(monkeypatch, tmp_path):
    assert SAMPLE.exists(), f"Missing sample dataset: {SAMPLE}"

    test_root = tmp_path / "e2e"
    monkeypatch.setattr(settings, "DATA_DIR", test_root)
    monkeypatch.setattr(settings, "UPLOADS_DIR", test_root / "uploads")
    monkeypatch.setattr(settings, "PROCESSED_DIR", test_root / "processed")
    monkeypatch.setattr(settings, "METADATA_DIR", test_root / "metadata")
    monkeypatch.setattr(settings, "DATASETS_DIR", test_root / "datasets")
    monkeypatch.setattr(settings, "SAMPLES_DIR", test_root / "samples")
    monkeypatch.setattr(settings, "BRAND_ASSETS_DIR", test_root / "branding")
    monkeypatch.setattr(settings, "DATASETS_METADATA_FILE", test_root / "metadata" / "datasets.json")
    monkeypatch.setattr(settings, "BRANDING_FILE", test_root / "metadata" / "branding.json")
    monkeypatch.setattr(settings, "SQL_QUERIES_FILE", test_root / "metadata" / "sql_queries.json")
    monkeypatch.setattr(settings, "THEME_STATE_FILE", test_root / "metadata" / "theme_state.json")
    ensure_data_directories()
    theme_manager.set_active("power_bi_professional")

    client = TestClient(app)
    content = SAMPLE.read_bytes()

    # 1) Upload real sample dataset
    upload = client.post(
        "/upload",
        files={"file": (SAMPLE.name, content, "text/csv")},
    )
    assert upload.status_code == 200, upload.text
    dataset_id = upload.json()["dataset_id"]

    # 2) Dataset ready + overview
    status = client.get(f"/datasets/{dataset_id}/status")
    assert status.status_code == 200
    assert status.json()["status"] == "ready"
    assert status.json()["row_count"] >= 20

    overview = client.get(f"/datasets/{dataset_id}/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["row_count"] >= 20
    assert "sales" in body["column_groups"]["numeric"]

    # 3) Analytics dashboard
    dashboard = client.get(f"/analytics/{dataset_id}/dashboard")
    assert dashboard.status_code == 200
    dash = dashboard.json()
    assert dash["kpi_cards"]

    # 4) Auth + org path
    email = f"e2e_{uuid4().hex[:8]}@example.com"
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": STRONG})
    assert reg.status_code == 201
    token = client.post("/api/v1/auth/login", json={"email": email, "password": STRONG}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 5) Storage upload of same dataset bytes
    storage = client.post(
        "/api/v1/storage/upload",
        files={"file": (SAMPLE.name, content, "text/csv")},
        params={"artifact_type": "dataset"},
        headers=headers,
    )
    assert storage.status_code == 201, storage.text

    # 6) Job submit
    job = client.post(
        "/api/v1/jobs",
        json={"job_type": "generic", "payload": {"dataset_id": dataset_id}, "inline": True},
        headers=headers,
    )
    assert job.status_code == 201

    # 7) Security headers + release validation
    health = client.get("/health")
    assert health.status_code == 200
    assert health.headers.get("X-Content-Type-Options") == "nosniff"
    assert health.json()["version"] == "1.0.0"

    validation = client.get("/api/v1/release/validation")
    assert validation.status_code == 200
    report = validation.json()
    required = {
        "authentication",
        "rbac",
        "organizations",
        "storage",
        "workflow",
        "evaluation",
        "jobs",
        "monitoring",
        "billing",
        "api_keys",
    }
    by_name = {c["name"]: c for c in report["checks"]}
    for name in required:
        assert name in by_name
        assert by_name[name]["ok"] is True, by_name[name]

    security = client.get("/api/v1/release/security/audit")
    assert security.status_code == 200
    assert security.json()["success"] is True
