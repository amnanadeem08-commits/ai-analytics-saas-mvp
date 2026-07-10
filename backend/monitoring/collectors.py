from __future__ import annotations

from typing import Any

from backend.monitoring.counters import export_metrics, set_gauge


def collect_runtime_metrics() -> dict[str, Any]:
    """Collect lightweight runtime gauges from subsystems."""
    snapshot = export_metrics()

    try:
        from backend.services import job_service

        stats = job_service.job_statistics()
        set_gauge("jobs_total", float(stats.get("total_jobs", 0)))
        set_gauge("jobs_queued_depth", float(stats.get("queued_depth", 0)))
        set_gauge("jobs_dead_letter_depth", float(stats.get("dead_letter_depth", 0)))
    except Exception:
        pass

    try:
        from backend.services import storage_service

        storage_stats = storage_service.storage_statistics()
        set_gauge("storage_total_objects", float(storage_stats.total_objects))
        set_gauge("storage_total_bytes", float(storage_stats.total_bytes))
    except Exception:
        pass

    try:
        from backend.queue.factory import active_backend

        set_gauge("queue_backend_active", 1.0, labels={"backend": active_backend()})
    except Exception:
        pass

    return export_metrics()
