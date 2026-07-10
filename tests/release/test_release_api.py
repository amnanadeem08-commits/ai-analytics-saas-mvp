from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.services import benchmark_service, release_validation_service

client = TestClient(app)


def test_benchmark_service_runs():
    report = benchmark_service.run_benchmarks()
    assert "categories" in report
    assert "workflow_latency_ms" in report["categories"]
    assert "memory" in report


def test_release_validation_subsystems():
    report = release_validation_service.validate_production_readiness()
    names = {c["name"] for c in report["checks"]}
    for required in (
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
    ):
        assert required in names
    subsystem_ok = [
        c
        for c in report["checks"]
        if c["name"]
        in {
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
    ]
    assert all(c["ok"] for c in subsystem_ok)


def test_release_api_endpoints():
    benchmarks = client.get("/api/v1/release/benchmarks")
    assert benchmarks.status_code == 200
    validation = client.get("/api/v1/release/validation")
    assert validation.status_code == 200
    perf = client.get("/api/v1/release/performance")
    assert perf.status_code == 200
    assert "memory" in perf.json()
