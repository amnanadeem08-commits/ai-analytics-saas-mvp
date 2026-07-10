from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_legacy_and_v1_health():
    legacy = client.get("/health")
    assert legacy.status_code == 200
    assert legacy.json()["status"] == "ok"

    v1 = client.get("/api/v1/health")
    assert v1.status_code == 200
    body = v1.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["api_gateway"] == "v1"
    assert "services" in body


def test_version_and_capabilities():
    version = client.get("/api/v1/version")
    assert version.status_code == 200
    assert version.json()["version"]
    assert "schema_versions" in version.json()

    caps = client.get("/api/v1/capabilities")
    assert caps.status_code == 200
    body = caps.json()
    assert body["success"] is True
    assert "ai_analyst_runtime" in body["capabilities"]
    assert "evaluation_framework" in body["capabilities"]
    assert "evaluation_runner" in body["workflow_runners"]
    assert "mock" in body["llm_providers"]


def test_openapi_generation():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths") or {}
    assert "/api/v1/health" in paths
    assert "/api/v1/analyst/analyze" in paths
    assert "/api/v1/workflow/execute" in paths
    assert "/api/v1/evaluation/export/{evaluation_id}" in paths
    assert "/api/v1/knowledge/ingest" in paths
    assert "/api/v1/capabilities" in paths
