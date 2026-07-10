from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.monitoring.registry import reset_registry

client = TestClient(app)


def setup_function():
    reset_registry()


def test_monitoring_endpoints():
    live = client.get("/api/v1/live")
    assert live.status_code == 200
    assert live.json()["alive"] is True

    ready = client.get("/api/v1/ready")
    assert ready.status_code == 200
    assert "ready" in ready.json()

    health = client.get("/api/v1/monitoring/health")
    assert health.status_code == 200
    assert health.json()["status"] in {"ok", "degraded"}

    metrics = client.get("/api/v1/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["success"] is True

    status = client.get("/api/v1/system/status")
    assert status.status_code == 200

    config = client.get("/api/v1/system/config")
    assert config.status_code == 200
    assert "config" in config.json()
    assert "jwt_secret" not in config.json()["config"]

    deps = client.get("/api/v1/system/dependencies")
    assert deps.status_code == 200
    assert "dependencies" in deps.json()


def test_legacy_health_still_works():
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 200


def test_request_id_header_on_api_call():
    response = client.get("/api/v1/live")
    assert response.headers.get("X-Request-ID")
    assert response.headers.get("X-Trace-ID")


def test_openapi_includes_monitoring_routes():
    schema = client.get("/openapi.json").json()
    paths = schema.get("paths") or {}
    assert "/api/v1/live" in paths
    assert "/api/v1/metrics" in paths
    assert "/api/v1/system/config" in paths
