from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from backend.api.auth_dependencies import get_current_user_dependency, require_permission
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.models.user_models import User
from backend.services import rbac_service
from backend.services.rbac_service import RBACError

router = APIRouter(prefix="/api/v1", tags=["RBAC"])


class RoleAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    role_id: str
    scope: str = "organization"
    organization_id: str = ""
    workspace_id: str = ""


class RoleRemoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment_id: str


def _handle(exc: Exception):
    if isinstance(exc, RBACError):
        raise_api_error(exc.status_code, exc.message)
    raise map_service_exception(exc) from exc


@router.get(
    "/roles",
    summary="List roles",
    description="Lists all roles (system + custom) with permissions and inheritance.",
)
def list_roles(current_user: User = Depends(get_current_user_dependency)) -> dict[str, Any]:
    roles = rbac_service.list_roles()
    return {"success": True, "count": len(roles), "roles": [r.model_dump() for r in roles]}


@router.get(
    "/permissions",
    summary="List permissions",
    description="Lists all known permissions and their scopes.",
)
def list_permissions(current_user: User = Depends(get_current_user_dependency)) -> dict[str, Any]:
    perms = rbac_service.list_permissions()
    return {"success": True, "count": len(perms), "permissions": [p.model_dump() for p in perms]}


@router.post(
    "/roles/assign",
    summary="Assign a role",
    description="Assigns a role to a user in a scope. Requires `rbac:assign`.",
)
def assign_role(
    request: RoleAssignRequest,
    current_user: User = Depends(require_permission("rbac:assign")),
) -> dict[str, Any]:
    try:
        assignment = rbac_service.assign_role(
            user_id=request.user_id,
            role_id=request.role_id,
            scope=request.scope,
            organization_id=request.organization_id,
            workspace_id=request.workspace_id,
            granted_by=current_user.user_id,
        )
        return {"success": True, "assignment": assignment.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post(
    "/roles/remove",
    summary="Remove a role assignment",
    description="Removes a role assignment by id. Requires `rbac:assign`.",
)
def remove_role(
    request: RoleRemoveRequest,
    current_user: User = Depends(require_permission("rbac:assign")),
) -> dict[str, Any]:
    try:
        removed = rbac_service.remove_role(request.assignment_id, removed_by=current_user.user_id)
        if not removed:
            raise_api_error(404, "Role assignment not found")
        return {"success": True, "removed": True}
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        _handle(exc)


@router.get(
    "/access/check",
    summary="Check access",
    description="Evaluates whether the current user holds a permission in the given scope.",
)
def check_access(
    permission: str = Query(...),
    organization_id: str = Query(default=""),
    workspace_id: str = Query(default=""),
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    evaluation = rbac_service.evaluate_access(
        user_id=current_user.user_id,
        permission=permission,
        organization_id=organization_id,
        workspace_id=workspace_id,
    )
    return {"success": True, "evaluation": evaluation.model_dump()}
