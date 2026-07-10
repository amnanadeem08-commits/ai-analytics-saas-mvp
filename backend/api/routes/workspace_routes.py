from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field

from backend.api.auth_dependencies import get_current_user_dependency, require_permission
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.models.user_models import User
from backend.services import workspace_service
from backend.services.workspace_service import WorkspaceError

router = APIRouter(prefix="/api/v1/workspaces", tags=["Workspaces"])


class WorkspaceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str
    name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    metadata: dict[str, Any] | None = None


def _handle(exc: Exception):
    if isinstance(exc, WorkspaceError):
        raise_api_error(exc.status_code, exc.message)
    raise map_service_exception(exc) from exc


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace",
    description="Creates a workspace in an organization. Requires `workspace:create`.",
)
def create_workspace(
    request: WorkspaceCreateRequest,
    current_user: User = Depends(require_permission("workspace:create")),
) -> dict[str, Any]:
    try:
        workspace = workspace_service.create_workspace(
            organization_id=request.organization_id,
            name=request.name,
            created_by=current_user.user_id,
            metadata=request.metadata,
        )
        return {"success": True, "workspace": workspace.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.get(
    "",
    summary="List workspaces",
    description="Lists workspaces for an organization. Requires `workspace:read`.",
)
def list_workspaces(
    organization_id: str = Query(...),
    include_archived: bool = Query(default=True),
    current_user: User = Depends(require_permission("workspace:read")),
) -> dict[str, Any]:
    workspaces = workspace_service.list_workspaces(organization_id, include_archived=include_archived)
    return {"success": True, "count": len(workspaces), "workspaces": [w.model_dump() for w in workspaces]}


@router.get(
    "/{workspace_id}",
    summary="Get a workspace",
    description="Returns workspace details, members, and a summary. Requires `workspace:read`.",
)
def get_workspace(
    workspace_id: str,
    current_user: User = Depends(require_permission("workspace:read")),
) -> dict[str, Any]:
    try:
        workspace = workspace_service.get_workspace(workspace_id)
        if workspace is None:
            raise_api_error(404, "Workspace not found")
        return {
            "success": True,
            "workspace": workspace.model_dump(),
            "members": workspace_service.list_workspace_members(workspace_id),
            "summary": workspace_service.workspace_summary(workspace_id),
        }
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        _handle(exc)


@router.put(
    "/{workspace_id}",
    summary="Update or rename a workspace",
    description="Updates workspace name/metadata. Requires `workspace:update`.",
)
def update_workspace(
    workspace_id: str,
    request: WorkspaceUpdateRequest,
    current_user: User = Depends(require_permission("workspace:update")),
) -> dict[str, Any]:
    try:
        workspace = workspace_service.update_workspace(
            workspace_id,
            name=request.name,
            metadata=request.metadata,
            actor_id=current_user.user_id,
        )
        return {"success": True, "workspace": workspace.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.delete(
    "/{workspace_id}",
    summary="Archive a workspace",
    description="Archives (soft-deletes) a workspace. Requires `workspace:delete`.",
)
def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(require_permission("workspace:delete")),
) -> dict[str, Any]:
    try:
        result = workspace_service.delete_workspace(workspace_id, actor_id=current_user.user_id)
        return {"success": True, **result}
    except Exception as exc:
        _handle(exc)


@router.post(
    "/{workspace_id}/restore",
    summary="Restore an archived workspace",
    description="Restores a previously archived workspace. Requires `workspace:update`.",
)
def restore_workspace(
    workspace_id: str,
    current_user: User = Depends(require_permission("workspace:update")),
) -> dict[str, Any]:
    try:
        workspace = workspace_service.restore_workspace(workspace_id, actor_id=current_user.user_id)
        return {"success": True, "workspace": workspace.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.get(
    "/{workspace_id}/members",
    summary="List workspace members",
    description="Lists workspace members with effective roles. Requires `workspace:read`.",
)
def list_workspace_members(
    workspace_id: str,
    current_user: User = Depends(require_permission("workspace:read")),
) -> dict[str, Any]:
    try:
        members = workspace_service.list_workspace_members(workspace_id)
        return {"success": True, "count": len(members), "members": members}
    except Exception as exc:
        _handle(exc)
