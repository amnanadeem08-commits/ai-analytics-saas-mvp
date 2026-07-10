from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.config.settings import get_app_settings
from backend.monitoring.collectors import collect_runtime_metrics
from backend.monitoring.health import (
    dependency_checks,
    health_report,
    liveness_report,
    readiness_report,
    system_status,
)

router = APIRouter(prefix="/api/v1", tags=["Monitoring"])


@router.get(
    "/monitoring/health",
    summary="Operational health check",
    description="Full health report with dependency probes (Sprint 8.5).",
)
def monitoring_health() -> dict[str, Any]:
    return {"success": True, **health_report()}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Returns whether the application is ready to receive traffic.",
)
def ready() -> dict[str, Any]:
    report = readiness_report()
    return {"success": True, **report}


@router.get(
    "/live",
    summary="Liveness probe",
    description="Returns whether the application process is alive.",
)
def live() -> dict[str, Any]:
    return {"success": True, **liveness_report()}


@router.get(
    "/metrics",
    summary="Application metrics",
    description="In-process metrics snapshot (counters, gauges, timers).",
)
def metrics() -> dict[str, Any]:
    settings = get_app_settings()
    if not settings.metrics_enabled:
        return {"success": True, "enabled": False, "metrics": {}}
    return {"success": True, "enabled": True, "metrics": collect_runtime_metrics()}


@router.get(
    "/system/status",
    summary="System status",
    description="Combined health + runtime metrics snapshot.",
)
def system_status_endpoint() -> dict[str, Any]:
    return {"success": True, **system_status()}


@router.get(
    "/system/config",
    summary="Read-only configuration",
    description="Returns redacted, read-only configuration values.",
)
def system_config() -> dict[str, Any]:
    settings = get_app_settings()
    return {"success": True, "config": settings.public_config()}


@router.get(
    "/system/dependencies",
    summary="Dependency status",
    description="Status of database, storage, queue, worker, and memory subsystems.",
)
def system_dependencies() -> dict[str, Any]:
    return {"success": True, "dependencies": dependency_checks()}
