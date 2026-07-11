from __future__ import annotations

"""End-to-end production smoke using the real sample sales dataset.

Covers upload → analytics → intelligence → auth/storage/jobs → release gates.
"""

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


def _isolate_data_dirs(monkeypatch, tmp_path) -> None:
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


def test_e2e_real_dataset_upload_analytics_and_release_gates(monkeypatch, tmp_path):
    assert SAMPLE.exists(), f"Missing sample dataset: {SAMPLE}"
    _isolate_data_dirs(monkeypatch, tmp_path)

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

    # 4) Intelligence + insights on real data
    data_insights = client.get(f"/intelligence/{dataset_id}/data-insights")
    assert data_insights.status_code == 200, data_insights.text
    assert data_insights.json().get("dataset_health", {}).get("row_count", 0) >= 20

    ai_business = client.get(f"/intelligence/{dataset_id}/ai-business-insights")
    assert ai_business.status_code == 200, ai_business.text
    assert isinstance(ai_business.json().get("cards"), list)

    domain = client.get(f"/intelligence/{dataset_id}/domain")
    assert domain.status_code == 200, domain.text
    assert domain.json().get("detected_domain") or domain.json().get("detection")

    insights = client.get(f"/insights/{dataset_id}")
    assert insights.status_code == 200, insights.text

    ask = client.post(
        f"/insights/{dataset_id}/ask",
        json={"question": "Which region has the strongest sales?"},
    )
    assert ask.status_code == 200, ask.text

    # 5) Auth + org path
    email = f"e2e_{uuid4().hex[:8]}@example.com"
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": STRONG})
    assert reg.status_code == 201
    token = client.post("/api/v1/auth/login", json={"email": email, "password": STRONG}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 6) Storage upload of same dataset bytes
    storage = client.post(
        "/api/v1/storage/upload",
        files={"file": (SAMPLE.name, content, "text/csv")},
        params={"artifact_type": "dataset"},
        headers=headers,
    )
    assert storage.status_code == 201, storage.text

    # 7) Job submit
    job = client.post(
        "/api/v1/jobs",
        json={"job_type": "generic", "payload": {"dataset_id": dataset_id}, "inline": True},
        headers=headers,
    )
    assert job.status_code == 201

    # 8) Health / live / ready + security headers + release validation
    health = client.get("/health")
    assert health.status_code == 200
    assert health.headers.get("X-Content-Type-Options") == "nosniff"
    assert health.json()["version"] == "1.0.0"

    live = client.get("/api/v1/live")
    assert live.status_code == 200
    ready = client.get("/api/v1/ready")
    assert ready.status_code == 200

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


def test_e2e_sample_dataset_row_coverage():
    """Guardrail: sample file remains substantial enough for smoke confidence."""
    assert SAMPLE.exists()
    lines = SAMPLE.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 21  # header + ≥20 rows
    header = lines[0].lower()
    for col in ("date", "sales", "region", "product"):
        assert col in header
