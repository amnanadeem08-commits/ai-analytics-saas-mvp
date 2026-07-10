from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from backend.api.auth_dependencies import get_current_user_dependency
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.models.user_models import User
from backend.services import admin_service, api_key_service, billing_service, subscription_service
from backend.services.admin_service import AdminError

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


class FeatureToggleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


def _handle(exc: Exception):
    if isinstance(exc, AdminError):
        raise_api_error(exc.status_code, exc.message)
    raise map_service_exception(exc) from exc


def _admin_user(current_user: User = Depends(get_current_user_dependency)) -> User:
    try:
        admin_service.require_admin(current_user)
    except AdminError as exc:
        raise_api_error(exc.status_code, exc.message)
    return current_user


@router.get("/dashboard", summary="Admin dashboard")
def dashboard(current_user: User = Depends(_admin_user)) -> dict[str, Any]:
    _ = current_user
    return {"success": True, "dashboard": admin_service.admin_dashboard()}


@router.get("/statistics", summary="System statistics")
def statistics(current_user: User = Depends(_admin_user)) -> dict[str, Any]:
    _ = current_user
    return {"success": True, "statistics": admin_service.system_statistics()}


@router.get("/users", summary="List users")
def users(current_user: User = Depends(_admin_user)) -> dict[str, Any]:
    _ = current_user
    users_list = admin_service.list_users()
    return {"success": True, "count": len(users_list), "users": users_list}


@router.get("/organizations", summary="List organizations")
def organizations(current_user: User = Depends(_admin_user)) -> dict[str, Any]:
    _ = current_user
    orgs = admin_service.list_organizations()
    return {"success": True, "count": len(orgs), "organizations": orgs}


@router.get("/workspaces", summary="List workspaces")
def workspaces(
    organization_id: str | None = Query(default=None),
    current_user: User = Depends(_admin_user),
) -> dict[str, Any]:
    _ = current_user
    items = admin_service.list_workspaces(organization_id)
    return {"success": True, "count": len(items), "workspaces": items}


@router.get("/subscriptions", summary="List subscriptions")
def subscriptions(current_user: User = Depends(_admin_user)) -> dict[str, Any]:
    _ = current_user
    subs = []
    for org in admin_service.list_organizations():
        sub = subscription_service.get_subscription(org["organization_id"])
        if sub:
            subs.append(sub.model_dump())
    return {"success": True, "count": len(subs), "subscriptions": subs}


@router.get("/api-keys", summary="List all API keys")
def all_api_keys(current_user: User = Depends(_admin_user)) -> dict[str, Any]:
    _ = current_user
    keys = api_key_service.list_keys()
    return {"success": True, "count": len(keys), "keys": [k.public_dict() for k in keys]}


@router.get("/usage", summary="Usage dashboard")
def usage(
    organization_id: str | None = Query(default=None),
    current_user: User = Depends(_admin_user),
) -> dict[str, Any]:
    _ = current_user
    return {"success": True, **admin_service.usage_dashboard(organization_id)}


@router.get("/audit", summary="Audit browser")
def audit(
    limit: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(_admin_user),
) -> dict[str, Any]:
    _ = current_user
    events = admin_service.audit_browser(limit=limit)
    return {"success": True, "count": len(events), "events": events}


@router.get("/invoices", summary="All invoices")
def invoices(current_user: User = Depends(_admin_user)) -> dict[str, Any]:
    _ = current_user
    items = billing_service.list_invoices()
    return {"success": True, "count": len(items), "invoices": [i.model_dump() for i in items]}


@router.get("/features", summary="Feature toggles")
def features(current_user: User = Depends(_admin_user)) -> dict[str, Any]:
    _ = current_user
    return {"success": True, "features": admin_service.get_feature_toggles()}


@router.put("/features/{feature_key}", summary="Set feature toggle")
def set_feature(
    feature_key: str,
    request: FeatureToggleRequest,
    current_user: User = Depends(_admin_user),
) -> dict[str, Any]:
    _ = current_user
    return {"success": True, "features": admin_service.set_feature_toggle(feature_key, request.enabled)}
