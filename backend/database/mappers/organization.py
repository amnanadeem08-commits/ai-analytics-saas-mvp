from __future__ import annotations

from backend.database.models.organization import (
    InvitationORM,
    OrganizationMemberORM,
    OrganizationORM,
    WorkspaceORM,
)
from backend.models.organization_models import (
    Invitation,
    Organization,
    OrganizationMember,
    Workspace,
)


def _dump(model) -> dict:
    return model.model_dump(mode="json")


# --- Organization ---------------------------------------------------------


def organization_to_orm(org: Organization, orm: OrganizationORM | None = None) -> OrganizationORM:
    orm = orm or OrganizationORM()
    orm.organization_id = org.organization_id
    orm.name = org.name
    orm.slug = org.slug
    orm.owner_id = org.owner_id
    orm.status = org.status.value if hasattr(org.status, "value") else str(org.status)
    orm.created_at = org.created_at
    orm.data = _dump(org)
    return orm


def orm_to_organization(orm: OrganizationORM) -> Organization:
    return Organization(**orm.data)


# --- Workspace ------------------------------------------------------------


def workspace_to_orm(ws: Workspace, orm: WorkspaceORM | None = None) -> WorkspaceORM:
    orm = orm or WorkspaceORM()
    orm.workspace_id = ws.workspace_id
    orm.organization_id = ws.organization_id
    orm.name = ws.name
    orm.slug = ws.slug
    orm.status = ws.status.value if hasattr(ws.status, "value") else str(ws.status)
    orm.created_at = ws.created_at
    orm.data = _dump(ws)
    return orm


def orm_to_workspace(orm: WorkspaceORM) -> Workspace:
    return Workspace(**orm.data)


# --- Member ---------------------------------------------------------------


def member_to_orm(member: OrganizationMember, orm: OrganizationMemberORM | None = None) -> OrganizationMemberORM:
    orm = orm or OrganizationMemberORM()
    orm.member_id = member.member_id
    orm.organization_id = member.organization_id
    orm.user_id = member.user_id
    orm.role_id = member.role_id
    orm.status = member.status.value if hasattr(member.status, "value") else str(member.status)
    orm.created_at = member.created_at
    orm.data = _dump(member)
    return orm


def orm_to_member(orm: OrganizationMemberORM) -> OrganizationMember:
    return OrganizationMember(**orm.data)


# --- Invitation -----------------------------------------------------------


def invitation_to_orm(inv: Invitation, orm: InvitationORM | None = None) -> InvitationORM:
    orm = orm or InvitationORM()
    orm.invitation_id = inv.invitation_id
    orm.organization_id = inv.organization_id
    orm.email = inv.email
    orm.role_id = inv.role_id
    orm.status = inv.status.value if hasattr(inv.status, "value") else str(inv.status)
    orm.token_hash = inv.token_hash
    orm.created_at = inv.created_at
    orm.data = _dump(inv)
    return orm


def orm_to_invitation(orm: InvitationORM) -> Invitation:
    return Invitation(**orm.data)
