from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field

from backend.api.auth_dependencies import get_current_user_dependency, require_permission
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.models.user_models import User
from backend.services import organization_service
from backend.services.organization_service import OrganizationError

router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])


class OrganizationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    slug: str = ""
    settings: dict[str, Any] = Field(default_factory=dict)


class OrganizationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    settings: dict[str, Any] | None = None


class InviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    role_id: str = "member"


class InvitationTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str


class TransferOwnershipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_owner_id: str


def _handle(exc: Exception):
    if isinstance(exc, OrganizationError):
        raise_api_error(exc.status_code, exc.message)
    raise map_service_exception(exc) from exc


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create an organization",
    description="Creates an organization with the current user as owner (owner role granted).",
)
def create_organization(
    request: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    try:
        org = organization_service.create_organization(
            name=request.name,
            owner_id=current_user.user_id,
            slug=request.slug,
            settings=request.settings,
        )
        return {"success": True, "organization": org.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.get(
    "",
    summary="List my organizations",
    description="Lists organizations where the current user is an active member.",
)
def list_organizations(
    include_archived: bool = Query(default=True),
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    orgs = organization_service.list_user_organizations(
        current_user.user_id, include_archived=include_archived
    )
    return {"success": True, "count": len(orgs), "organizations": [o.model_dump() for o in orgs]}


@router.get(
    "/{organization_id}",
    summary="Get an organization",
    description="Returns organization details and a summary. Requires `organization:read`.",
)
def get_organization(
    organization_id: str,
    current_user: User = Depends(require_permission("organization:read")),
) -> dict[str, Any]:
    try:
        org = organization_service.get_organization(organization_id)
        if org is None:
            raise_api_error(404, "Organization not found")
        summary = organization_service.organization_summary(organization_id)
        return {"success": True, "organization": org.model_dump(), "summary": summary}
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        _handle(exc)


@router.put(
    "/{organization_id}",
    summary="Update an organization",
    description="Updates organization name/settings. Requires `organization:update`.",
)
def update_organization(
    organization_id: str,
    request: OrganizationUpdateRequest,
    current_user: User = Depends(require_permission("organization:update")),
) -> dict[str, Any]:
    try:
        org = organization_service.update_organization(
            organization_id,
            name=request.name,
            settings=request.settings,
            actor_id=current_user.user_id,
        )
        return {"success": True, "organization": org.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.delete(
    "/{organization_id}",
    summary="Archive an organization",
    description="Archives (soft-deletes) an organization. Requires `organization:delete`.",
)
def archive_organization(
    organization_id: str,
    current_user: User = Depends(require_permission("organization:delete")),
) -> dict[str, Any]:
    try:
        org = organization_service.archive_organization(organization_id, actor_id=current_user.user_id)
        return {"success": True, "organization": org.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post(
    "/{organization_id}/restore",
    summary="Restore an archived organization",
    description="Restores a previously archived organization. Requires `organization:update`.",
)
def restore_organization(
    organization_id: str,
    current_user: User = Depends(require_permission("organization:update")),
) -> dict[str, Any]:
    try:
        org = organization_service.restore_organization(organization_id, actor_id=current_user.user_id)
        return {"success": True, "organization": org.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post(
    "/{organization_id}/invite",
    summary="Invite a member",
    description="Creates an invitation. Requires `member:invite`. Returns a dev invitation token.",
)
def invite_member(
    organization_id: str,
    request: InviteRequest,
    current_user: User = Depends(require_permission("member:invite")),
) -> dict[str, Any]:
    try:
        result = organization_service.invite_member(
            organization_id=organization_id,
            email=request.email,
            role_id=request.role_id,
            invited_by=current_user.user_id,
        )
        return {
            "success": True,
            "invitation": result["invitation"].model_dump(),
            "invitation_token": result["invitation_token"],
        }
    except Exception as exc:
        _handle(exc)


@router.post(
    "/invitations/accept",
    summary="Accept an invitation",
    description="Accepts an invitation using its token and joins the organization.",
)
def accept_invitation(
    request: InvitationTokenRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    try:
        member = organization_service.accept_invitation(
            token=request.token,
            user_id=current_user.user_id,
            email=current_user.email,
        )
        return {"success": True, "member": member.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post(
    "/invitations/decline",
    summary="Decline an invitation",
    description="Declines a pending invitation using its token.",
)
def decline_invitation(
    request: InvitationTokenRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    try:
        result = organization_service.decline_invitation(token=request.token, user_id=current_user.user_id)
        return {"success": True, **result}
    except Exception as exc:
        _handle(exc)


@router.get(
    "/{organization_id}/members",
    summary="List members",
    description="Lists organization members. Requires `member:read`.",
)
def list_members(
    organization_id: str,
    current_user: User = Depends(require_permission("member:read")),
) -> dict[str, Any]:
    members = organization_service.list_members(organization_id)
    return {"success": True, "count": len(members), "members": [m.model_dump() for m in members]}


@router.delete(
    "/{organization_id}/members/{member_user_id}",
    summary="Remove a member",
    description="Removes a member from the organization. Requires `member:remove`.",
)
def remove_member(
    organization_id: str,
    member_user_id: str,
    current_user: User = Depends(require_permission("member:remove")),
) -> dict[str, Any]:
    try:
        result = organization_service.remove_member(
            organization_id=organization_id,
            user_id=member_user_id,
            actor_id=current_user.user_id,
        )
        return {"success": True, **result}
    except Exception as exc:
        _handle(exc)


@router.post(
    "/{organization_id}/transfer-ownership",
    summary="Transfer ownership",
    description="Transfers organization ownership to another active member. Requires `organization:transfer`.",
)
def transfer_ownership(
    organization_id: str,
    request: TransferOwnershipRequest,
    current_user: User = Depends(require_permission("organization:transfer")),
) -> dict[str, Any]:
    try:
        org = organization_service.transfer_ownership(
            organization_id=organization_id,
            new_owner_id=request.new_owner_id,
            actor_id=current_user.user_id,
        )
        return {"success": True, "organization": org.model_dump()}
    except Exception as exc:
        _handle(exc)
