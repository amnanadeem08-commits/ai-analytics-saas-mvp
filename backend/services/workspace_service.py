from __future__ import annotations

"""Workspace service (Sprint 8.1).

Workspaces belong to organizations and are storage-independent. Membership is
derived from organization membership (workspace-scoped role overrides are
handled by rbac_service).
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.models.organization_models import (
    Workspace,
    WorkspaceMetadata,
    WorkspaceStatus,
)
from backend.models.user_models import AuthAuditEvent


class WorkspaceError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _repos():
    from backend.repositories.registry import get_repositories

    return get_repositories()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(name or "").strip().lower()).strip("-")
    return slug or f"ws-{uuid.uuid4().hex[:8]}"


def _audit(event_type: str, *, user_id: str = "", details: dict[str, Any] | None = None) -> None:
    _repos().audit.add(
        AuthAuditEvent(
            event_id=_uid("evt"),
            event_type=event_type,
            user_id=user_id,
            success=True,
            timestamp=_now_iso(),
            details=dict(details or {}),
        )
    )


def create_workspace(
    *,
    organization_id: str,
    name: str,
    created_by: str = "",
    metadata: dict[str, Any] | None = None,
) -> Workspace:
    repos = _repos()
    org = repos.organizations.get(organization_id)
    if org is None:
        raise WorkspaceError("Organization not found", status_code=404)
    if not str(name or "").strip():
        raise WorkspaceError("Workspace name is required", status_code=422)

    existing = repos.workspaces.list(organization_id=organization_id)
    if len(existing) >= org.settings.max_workspaces:
        raise WorkspaceError("Workspace limit reached for this organization", status_code=409)

    now = _now_iso()
    workspace = Workspace(
        workspace_id=_uid("wsp"),
        organization_id=organization_id,
        name=name.strip(),
        slug=_slugify(name),
        status=WorkspaceStatus.active,
        created_by=created_by,
        workspace_metadata=WorkspaceMetadata(**(metadata or {})),
        created_at=now,
        updated_at=now,
    )
    repos.workspaces.add(workspace)
    _audit("workspace_created", user_id=created_by, details={"organization_id": organization_id, "workspace_id": workspace.workspace_id})
    return workspace


def get_workspace(workspace_id: str) -> Workspace | None:
    return _repos().workspaces.get(workspace_id)


def rename_workspace(workspace_id: str, *, name: str, actor_id: str = "") -> Workspace:
    repos = _repos()
    workspace = repos.workspaces.get(workspace_id)
    if workspace is None:
        raise WorkspaceError("Workspace not found", status_code=404)
    if not str(name or "").strip():
        raise WorkspaceError("Workspace name is required", status_code=422)
    workspace.name = name.strip()
    workspace.slug = _slugify(name)
    workspace.updated_at = _now_iso()
    repos.workspaces.update(workspace)
    _audit("workspace_renamed", user_id=actor_id, details={"workspace_id": workspace_id})
    return workspace


def update_workspace(
    workspace_id: str,
    *,
    name: str | None = None,
    metadata: dict[str, Any] | None = None,
    actor_id: str = "",
) -> Workspace:
    repos = _repos()
    workspace = repos.workspaces.get(workspace_id)
    if workspace is None:
        raise WorkspaceError("Workspace not found", status_code=404)
    if name is not None and name.strip():
        workspace.name = name.strip()
        workspace.slug = _slugify(name)
    if metadata is not None:
        merged = {**workspace.workspace_metadata.model_dump(), **metadata}
        workspace.workspace_metadata = WorkspaceMetadata(**merged)
    workspace.updated_at = _now_iso()
    repos.workspaces.update(workspace)
    _audit("workspace_updated", user_id=actor_id, details={"workspace_id": workspace_id})
    return workspace


def archive_workspace(workspace_id: str, *, actor_id: str = "") -> Workspace:
    repos = _repos()
    workspace = repos.workspaces.get(workspace_id)
    if workspace is None:
        raise WorkspaceError("Workspace not found", status_code=404)
    workspace.status = WorkspaceStatus.archived
    workspace.archived_at = _now_iso()
    workspace.updated_at = workspace.archived_at
    repos.workspaces.update(workspace)
    _audit("workspace_archived", user_id=actor_id, details={"workspace_id": workspace_id})
    return workspace


def restore_workspace(workspace_id: str, *, actor_id: str = "") -> Workspace:
    repos = _repos()
    workspace = repos.workspaces.get(workspace_id)
    if workspace is None:
        raise WorkspaceError("Workspace not found", status_code=404)
    workspace.status = WorkspaceStatus.active
    workspace.archived_at = ""
    workspace.updated_at = _now_iso()
    repos.workspaces.update(workspace)
    _audit("workspace_restored", user_id=actor_id, details={"workspace_id": workspace_id})
    return workspace


def delete_workspace(workspace_id: str, *, actor_id: str = "") -> dict[str, Any]:
    """Soft-delete via archive to keep isolation guarantees (no hard delete)."""
    archive_workspace(workspace_id, actor_id=actor_id)
    return {"archived": True, "workspace_id": workspace_id}


def list_workspaces(organization_id: str, *, include_archived: bool = True) -> list[Workspace]:
    return _repos().workspaces.list(organization_id=organization_id, include_archived=include_archived)


def list_workspace_members(workspace_id: str) -> list[dict[str, Any]]:
    """Workspace members = active organization members of the owning org.

    Workspace-scoped role overrides (rbac_service) are surfaced in ``role_id``.
    """
    from backend.models.organization_models import MembershipStatus

    repos = _repos()
    workspace = repos.workspaces.get(workspace_id)
    if workspace is None:
        raise WorkspaceError("Workspace not found", status_code=404)
    members = repos.memberships.list(organization_id=workspace.organization_id)
    overrides = {
        a.user_id: a.role_id
        for a in repos.role_assignments.list(workspace_id=workspace_id)
    }
    result = []
    for member in members:
        if member.status != MembershipStatus.active:
            continue
        result.append(
            {
                "user_id": member.user_id,
                "email": member.email,
                "organization_role": member.role_id,
                "workspace_role": overrides.get(member.user_id, ""),
                "role_id": overrides.get(member.user_id) or member.role_id,
            }
        )
    return result


def workspace_summary(workspace_id: str) -> dict[str, Any]:
    repos = _repos()
    workspace = repos.workspaces.get(workspace_id)
    if workspace is None:
        raise WorkspaceError("Workspace not found", status_code=404)
    members = list_workspace_members(workspace_id)
    return {
        "workspace_id": workspace.workspace_id,
        "organization_id": workspace.organization_id,
        "name": workspace.name,
        "status": workspace.status.value,
        "member_count": len(members),
        "created_by": workspace.created_by,
        "created_at": workspace.created_at,
    }
