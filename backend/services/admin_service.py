from __future__ import annotations

"""Admin portal service (Sprint 8.6)."""

from typing import Any

from backend.models.user_models import UserRole
from backend.services import api_key_service, billing_service, subscription_service, usage_service


class AdminError(Exception):
    def __init__(self, message: str, *, status_code: int = 403):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


_FEATURE_TOGGLES: dict[str, bool] = {
    "ai_analyst": True,
    "workflows": True,
    "knowledge": True,
    "evaluation": True,
    "billing": True,
    "api_keys": True,
    "admin_portal": True,
}


def reset_admin() -> None:
    global _FEATURE_TOGGLES
    _FEATURE_TOGGLES = {
        "ai_analyst": True,
        "workflows": True,
        "knowledge": True,
        "evaluation": True,
        "billing": True,
        "api_keys": True,
        "admin_portal": True,
    }


def require_admin(user) -> None:
    role = getattr(user, "role", None)
    if role and getattr(role, "value", str(role)) == UserRole.admin.value:
        return
    meta = getattr(user, "metadata", None) or {}
    if isinstance(meta, dict) and meta.get("platform_admin"):
        return
    raise AdminError("Platform admin access required", status_code=403)


def list_users() -> list[dict[str, Any]]:
    from backend.services.auth_service import list_users as _list

    return [u.public_dict() for u in _list()]


def list_organizations() -> list[dict[str, Any]]:
    from backend.repositories.registry import get_repositories

    repos = get_repositories()
    orgs = repos.organizations.list()
    return [o.model_dump() for o in orgs]


def list_workspaces(organization_id: str | None = None) -> list[dict[str, Any]]:
    from backend.repositories.registry import get_repositories

    repos = get_repositories()
    workspaces = repos.workspaces.list(organization_id=organization_id)
    return [w.model_dump() for w in workspaces]


def admin_dashboard() -> dict[str, Any]:
    from backend.services import job_service, storage_service
    from backend.monitoring.health import health_report

    subs = [subscription_service.get_subscription(o["organization_id"]) for o in list_organizations()]
    active_subs = [s for s in subs if s is not None]
    return {
        "health": health_report(),
        "plans": len(subscription_service.list_plans()),
        "active_subscriptions": len(active_subs),
        "api_keys": len(api_key_service.list_keys()),
        "usage_records": len(usage_service.list_usage()),
        "invoices": len(billing_service.list_invoices()),
        "jobs": job_service.job_statistics(),
        "storage": storage_service.storage_statistics().model_dump(),
        "feature_toggles": dict(_FEATURE_TOGGLES),
    }


def usage_dashboard(organization_id: str | None = None) -> dict[str, Any]:
    if organization_id:
        return usage_service.usage_summary(organization_id)
    summaries = [usage_service.usage_summary(o["organization_id"]) for o in list_organizations()]
    return {"organizations": summaries}


def audit_browser(*, limit: int = 50) -> list[dict[str, Any]]:
    from backend.services.auth_service import list_audit_events

    events = list_audit_events(limit=limit)
    return [e.model_dump() for e in events]


def get_feature_toggles() -> dict[str, bool]:
    return dict(_FEATURE_TOGGLES)


def set_feature_toggle(feature_key: str, enabled: bool) -> dict[str, bool]:
    _FEATURE_TOGGLES[feature_key] = bool(enabled)
    return dict(_FEATURE_TOGGLES)


def system_statistics() -> dict[str, Any]:
    from backend.monitoring.collectors import collect_runtime_metrics

    counts: dict[str, int] = {}
    for org in list_organizations():
        sub = subscription_service.get_subscription(org["organization_id"])
        if sub:
            counts[sub.plan_id] = counts.get(sub.plan_id, 0) + 1
    return {
        "metrics": collect_runtime_metrics(),
        "subscriptions_by_plan": counts,
        "total_usage_records": len(usage_service.list_usage()),
    }
