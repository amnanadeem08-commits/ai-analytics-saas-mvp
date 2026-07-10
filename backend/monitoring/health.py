from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.config.settings import get_app_settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def check_configuration() -> dict[str, Any]:
    try:
        from backend.config.config_loader import load_and_validate

        _, validation = load_and_validate()
        return {"status": "ok" if validation["valid"] else "degraded", "profile": validation["profile"], "issues": validation["issues"]}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def check_database() -> dict[str, Any]:
    try:
        from backend.database.config import get_database_config

        cfg = get_database_config()
        if not cfg.uses_database:
            return {"status": "skipped", "backend": cfg.storage_backend, "message": "in-memory backend"}
        from backend.database.database import health_check

        result = health_check()
        return {"status": "ok" if result.get("connected") else "unavailable", **result}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def check_storage() -> dict[str, Any]:
    try:
        from backend.storage.factory import active_provider, get_backend

        backend = get_backend()
        probe_key = "__health_probe__"
        backend.write(probe_key, b"ok")
        ok = backend.read(probe_key) == b"ok"
        backend.delete(probe_key)
        return {"status": "ok" if ok else "unavailable", "provider": active_provider()}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def check_queue() -> dict[str, Any]:
    try:
        from backend.queue.factory import active_backend, get_queue

        queue = get_queue()
        depth = queue.size()
        return {"status": "ok", "backend": active_backend(), "queued_depth": depth}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def check_worker() -> dict[str, Any]:
    try:
        from backend.workers import get_worker

        worker = get_worker()
        health = worker.health()
        status = "ok" if health.get("status") in {"idle", "busy", "stopped"} else "degraded"
        return {"status": status, **health}
    except Exception as exc:
        return {"status": "skipped", "message": str(exc)}


def check_memory_subsystem() -> dict[str, Any]:
    try:
        from backend.api.dependencies import get_memory_service

        store = get_memory_service().get_memory_store()
        _ = store
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def dependency_checks() -> dict[str, Any]:
    return {
        "configuration": check_configuration(),
        "database": check_database(),
        "storage": check_storage(),
        "queue": check_queue(),
        "worker": check_worker(),
        "memory": check_memory_subsystem(),
    }


def overall_status(checks: dict[str, Any]) -> str:
    statuses = [str(v.get("status", "unknown")) for v in checks.values()]
    if all(s in {"ok", "skipped"} for s in statuses):
        return "ok"
    if any(s == "unavailable" for s in statuses):
        return "degraded"
    return "degraded"


def health_report() -> dict[str, Any]:
    settings = get_app_settings()
    checks = dependency_checks()
    return {
        "status": overall_status(checks),
        "timestamp": _now(),
        "app": settings.app_name,
        "version": settings.api_version,
        "profile": settings.profile.value,
        "dependencies": checks,
    }


def readiness_report() -> dict[str, Any]:
    checks = dependency_checks()
    critical = {k: checks[k] for k in ("configuration", "database", "storage", "queue") if k in checks}
    ready = all(v.get("status") in {"ok", "skipped"} for v in critical.values())
    return {"ready": ready, "status": "ready" if ready else "not_ready", "checks": critical, "timestamp": _now()}


def liveness_report() -> dict[str, Any]:
    return {"alive": True, "status": "alive", "timestamp": _now()}


def system_status() -> dict[str, Any]:
    report = health_report()
    try:
        from backend.monitoring.collectors import collect_runtime_metrics

        report["metrics_snapshot"] = collect_runtime_metrics()
    except Exception:
        report["metrics_snapshot"] = {}
    return report
