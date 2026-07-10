from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.performance import memory_snapshot, pool_status, query_stats
from backend.reliability import circuit_status, is_shutting_down
from backend.security.cors_policy import cors_origins, validate_cors_config
from backend.security.dependency_audit import audit_dependencies
from backend.security.secrets_validation import validate_secrets
from backend.services import benchmark_service, release_validation_service

router = APIRouter(prefix="/api/v1/release", tags=["Release"])


@router.get("/benchmarks", summary="Run in-process benchmarks")
def benchmarks() -> dict[str, Any]:
    return {"success": True, "benchmarks": benchmark_service.run_benchmarks()}


@router.get("/validation", summary="Production readiness validation")
def validation() -> dict[str, Any]:
    report = release_validation_service.validate_production_readiness()
    return {"success": True, **report}


@router.get("/security/audit", summary="Security audit snapshot")
def security_audit() -> dict[str, Any]:
    return {
        "success": True,
        "secrets": validate_secrets(),
        "cors": {"origins": cors_origins(), "issues": validate_cors_config()},
        "dependencies": audit_dependencies(),
        "shutting_down": is_shutting_down(),
    }


@router.get("/recovery", summary="Attempt subsystem recovery")
def recovery() -> dict[str, Any]:
    from backend.reliability.health_recovery import attempt_recovery

    return {"success": True, **attempt_recovery()}


@router.get("/performance", summary="Performance snapshot")
def performance_snapshot() -> dict[str, Any]:
    return {
        "success": True,
        "memory": memory_snapshot(),
        "pool": pool_status(),
        "slow_queries": query_stats()[-20:],
        "circuits": circuit_status(),
    }
