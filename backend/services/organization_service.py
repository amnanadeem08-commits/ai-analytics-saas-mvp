from __future__ import annotations

"""Organization service (Sprint 8.1).

Storage-independent org + membership + invitation logic. Depends only on
repository interfaces via the registry and on rbac_service for role grants.
"""

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.organization_models import (
    Invitation,
    InvitationStatus,
    Organization,
    OrganizationMember,
    OrganizationSettings,
    OrganizationStatus,
    MembershipStatus,
)
from backend.models.user_models import AuthAuditEvent
from backend.security.password_service import generate_token, hash_token


class OrganizationError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


INVITATION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


def _repos():
    from backend.repositories.registry import get_repositories

    return get_repositories()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat().replace("+00:00", "Z")


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(name or "").strip().lower()).strip("-")
    return slug or f"org-{uuid.uuid4().hex[:8]}"


def _audit(event_type: str, *, user_id: str = "", success: bool = True, details: dict[str, Any] | None = None) -> None:
    _repos().audit.add(
        AuthAuditEvent(
            event_id=_uid("evt"),
            event_type=event_type,
            user_id=user_id,
            success=success,
            timestamp=_now_iso(),
            details=dict(details or {}),
        )
    )


def _is_expired(iso_ts: str) -> bool:
    if not iso_ts:
        return True
    try:
        parsed = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return True
    return parsed < _now()


# ---------------------------------------------------------------------------
# Organization CRUD
# ---------------------------------------------------------------------------


def create_organization(
    *,
    name: str,
    owner_id: str,
    slug: str = "",
    settings: dict[str, Any] | None = None,
) -> Organization:
    from backend.services import rbac_service

    if not str(name or "").strip():
        raise OrganizationError("Organization name is required", status_code=422)
    if not owner_id:
        raise OrganizationError("owner_id is required", status_code=422)
    repos = _repos()
    resolved_slug = slug or _slugify(name)
    if repos.organizations.get_by_slug(resolved_slug) is not None:
        resolved_slug = f"{resolved_slug}-{uuid.uuid4().hex[:6]}"

    now = _now_iso()
    org = Organization(
        organization_id=_uid("org"),
        name=name.strip(),
        slug=resolved_slug,
        owner_id=owner_id,
        status=OrganizationStatus.active,
        settings=OrganizationSettings(**(settings or {})),
        created_at=now,
        updated_at=now,
    )
    repos.organizations.add(org)

    # Owner becomes an active member with the owner role.
    member = OrganizationMember(
        member_id=_uid("mbr"),
        organization_id=org.organization_id,
        user_id=owner_id,
        role_id="owner",
        status=MembershipStatus.active,
        joined_at=now,
        created_at=now,
        updated_at=now,
    )
    repos.memberships.add(member)
    rbac_service.assign_role(
        user_id=owner_id,
        role_id="owner",
        scope="organization",
        organization_id=org.organization_id,
        granted_by=owner_id,
    )
    _audit("organization_created", user_id=owner_id, details={"organization_id": org.organization_id})
    return org


def get_organization(organization_id: str) -> Organization | None:
    return _repos().organizations.get(organization_id)


def update_organization(
    organization_id: str,
    *,
    name: str | None = None,
    settings: dict[str, Any] | None = None,
    actor_id: str = "",
) -> Organization:
    repos = _repos()
    org = repos.organizations.get(organization_id)
    if org is None:
        raise OrganizationError("Organization not found", status_code=404)
    if name is not None:
        org.name = name.strip()
    if settings is not None:
        merged = {**org.settings.model_dump(), **settings}
        org.settings = OrganizationSettings(**merged)
    org.updated_at = _now_iso()
    repos.organizations.update(org)
    _audit("organization_updated", user_id=actor_id, details={"organization_id": organization_id})
    return org


def archive_organization(organization_id: str, *, actor_id: str = "") -> Organization:
    repos = _repos()
    org = repos.organizations.get(organization_id)
    if org is None:
        raise OrganizationError("Organization not found", status_code=404)
    org.status = OrganizationStatus.archived
    org.archived_at = _now_iso()
    org.updated_at = org.archived_at
    repos.organizations.update(org)
    _audit("organization_archived", user_id=actor_id, details={"organization_id": organization_id})
    return org


def restore_organization(organization_id: str, *, actor_id: str = "") -> Organization:
    repos = _repos()
    org = repos.organizations.get(organization_id)
    if org is None:
        raise OrganizationError("Organization not found", status_code=404)
    org.status = OrganizationStatus.active
    org.archived_at = ""
    org.updated_at = _now_iso()
    repos.organizations.update(org)
    _audit("organization_restored", user_id=actor_id, details={"organization_id": organization_id})
    return org


def list_organizations(*, owner_id: str | None = None, include_archived: bool = True) -> list[Organization]:
    return _repos().organizations.list(owner_id=owner_id, include_archived=include_archived)


def list_user_organizations(user_id: str, *, include_archived: bool = True) -> list[Organization]:
    """Organizations where the user is an active member."""
    repos = _repos()
    org_ids = {
        m.organization_id
        for m in repos.memberships.list(user_id=user_id)
        if m.status == MembershipStatus.active
    }
    results = []
    for org_id in org_ids:
        org = repos.organizations.get(org_id)
        if org is None:
            continue
        if not include_archived and org.status == OrganizationStatus.archived:
            continue
        results.append(org)
    results.sort(key=lambda o: o.created_at)
    return results


# ---------------------------------------------------------------------------
# Membership + invitations
# ---------------------------------------------------------------------------


def list_members(organization_id: str) -> list[OrganizationMember]:
    return _repos().memberships.list(organization_id=organization_id)


def get_member(organization_id: str, user_id: str) -> OrganizationMember | None:
    return _repos().memberships.find(organization_id=organization_id, user_id=user_id)


def invite_member(
    *,
    organization_id: str,
    email: str,
    role_id: str = "member",
    invited_by: str = "",
) -> dict[str, Any]:
    repos = _repos()
    org = repos.organizations.get(organization_id)
    if org is None:
        raise OrganizationError("Organization not found", status_code=404)
    if repos.roles.get(role_id) is None:
        raise OrganizationError(f"Unknown role: {role_id}", status_code=422)

    raw_token = generate_token()
    now = _now_iso()
    invitation = Invitation(
        invitation_id=_uid("inv"),
        organization_id=organization_id,
        email=str(email or "").strip().lower(),
        role_id=role_id,
        status=InvitationStatus.pending,
        invited_by=invited_by,
        token_hash=hash_token(raw_token),
        created_at=now,
        expires_at=(_now() + timedelta(seconds=INVITATION_TTL_SECONDS)).isoformat().replace("+00:00", "Z"),
    )
    repos.invitations.add(invitation)
    _audit("member_invited", user_id=invited_by, details={"organization_id": organization_id, "email": invitation.email, "role_id": role_id})
    return {"invitation": invitation, "invitation_token": raw_token}


def accept_invitation(*, token: str, user_id: str, email: str = "") -> OrganizationMember:
    from backend.services import rbac_service

    repos = _repos()
    invitation = repos.invitations.find_by_token_hash(hash_token(token))
    if invitation is None or invitation.status != InvitationStatus.pending:
        raise OrganizationError("Invalid or already-used invitation", status_code=400)
    if _is_expired(invitation.expires_at):
        invitation.status = InvitationStatus.expired
        repos.invitations.update(invitation)
        raise OrganizationError("Invitation has expired", status_code=400)

    existing = repos.memberships.find(organization_id=invitation.organization_id, user_id=user_id)
    now = _now_iso()
    if existing is not None:
        existing.status = MembershipStatus.active
        existing.role_id = invitation.role_id
        existing.updated_at = now
        member = repos.memberships.update(existing)
    else:
        member = repos.memberships.add(
            OrganizationMember(
                member_id=_uid("mbr"),
                organization_id=invitation.organization_id,
                user_id=user_id,
                email=email or invitation.email,
                role_id=invitation.role_id,
                status=MembershipStatus.active,
                invited_by=invitation.invited_by,
                joined_at=now,
                created_at=now,
                updated_at=now,
            )
        )
    invitation.status = InvitationStatus.accepted
    invitation.responded_at = now
    repos.invitations.update(invitation)
    rbac_service.assign_role(
        user_id=user_id,
        role_id=invitation.role_id,
        scope="organization",
        organization_id=invitation.organization_id,
        granted_by=invitation.invited_by,
    )
    _audit("invitation_accepted", user_id=user_id, details={"organization_id": invitation.organization_id})
    return member


def decline_invitation(*, token: str, user_id: str = "") -> dict[str, Any]:
    repos = _repos()
    invitation = repos.invitations.find_by_token_hash(hash_token(token))
    if invitation is None or invitation.status != InvitationStatus.pending:
        raise OrganizationError("Invalid or already-used invitation", status_code=400)
    invitation.status = InvitationStatus.declined
    invitation.responded_at = _now_iso()
    repos.invitations.update(invitation)
    _audit("invitation_declined", user_id=user_id, details={"organization_id": invitation.organization_id})
    return {"declined": True, "organization_id": invitation.organization_id}


def list_invitations(organization_id: str) -> list[Invitation]:
    return _repos().invitations.list(organization_id=organization_id)


def remove_member(*, organization_id: str, user_id: str, actor_id: str = "") -> dict[str, Any]:
    from backend.services import rbac_service

    repos = _repos()
    org = repos.organizations.get(organization_id)
    if org is None:
        raise OrganizationError("Organization not found", status_code=404)
    if org.owner_id == user_id:
        raise OrganizationError("Cannot remove the organization owner; transfer ownership first", status_code=409)
    member = repos.memberships.find(organization_id=organization_id, user_id=user_id)
    if member is None:
        raise OrganizationError("Member not found", status_code=404)
    member.status = MembershipStatus.removed
    member.updated_at = _now_iso()
    repos.memberships.update(member)
    # Revoke org-scoped role assignments for this user.
    for assignment in repos.role_assignments.list(user_id=user_id, organization_id=organization_id):
        rbac_service.remove_role(assignment.assignment_id, removed_by=actor_id)
    _audit("member_removed", user_id=actor_id, details={"organization_id": organization_id, "target_user": user_id})
    return {"removed": True, "user_id": user_id}


def transfer_ownership(*, organization_id: str, new_owner_id: str, actor_id: str = "") -> Organization:
    from backend.services import rbac_service

    repos = _repos()
    org = repos.organizations.get(organization_id)
    if org is None:
        raise OrganizationError("Organization not found", status_code=404)
    new_member = repos.memberships.find(organization_id=organization_id, user_id=new_owner_id)
    if new_member is None or new_member.status != MembershipStatus.active:
        raise OrganizationError("New owner must be an active member", status_code=422)

    previous_owner = org.owner_id
    org.owner_id = new_owner_id
    org.updated_at = _now_iso()
    repos.organizations.update(org)

    # New owner gets the owner role; previous owner downgraded to admin.
    new_member.role_id = "owner"
    new_member.updated_at = _now_iso()
    repos.memberships.update(new_member)
    rbac_service.assign_role(
        user_id=new_owner_id, role_id="owner", scope="organization",
        organization_id=organization_id, granted_by=actor_id,
    )
    prev_member = repos.memberships.find(organization_id=organization_id, user_id=previous_owner)
    if prev_member is not None:
        prev_member.role_id = "admin"
        prev_member.updated_at = _now_iso()
        repos.memberships.update(prev_member)
        rbac_service.assign_role(
            user_id=previous_owner, role_id="admin", scope="organization",
            organization_id=organization_id, granted_by=actor_id,
        )
    _audit(
        "ownership_transferred",
        user_id=actor_id,
        details={"organization_id": organization_id, "from": previous_owner, "to": new_owner_id},
    )
    return org


# ---------------------------------------------------------------------------
# Workspaces + summary
# ---------------------------------------------------------------------------


def list_workspaces(organization_id: str, *, include_archived: bool = True) -> list:
    return _repos().workspaces.list(organization_id=organization_id, include_archived=include_archived)


def organization_summary(organization_id: str) -> dict[str, Any]:
    repos = _repos()
    org = repos.organizations.get(organization_id)
    if org is None:
        raise OrganizationError("Organization not found", status_code=404)
    members = repos.memberships.list(organization_id=organization_id)
    workspaces = repos.workspaces.list(organization_id=organization_id)
    active_members = [m for m in members if m.status == MembershipStatus.active]
    pending_invites = [
        i for i in repos.invitations.list(organization_id=organization_id)
        if i.status == InvitationStatus.pending
    ]
    return {
        "organization_id": org.organization_id,
        "name": org.name,
        "status": org.status.value,
        "owner_id": org.owner_id,
        "member_count": len(active_members),
        "workspace_count": len(workspaces),
        "pending_invitations": len(pending_invites),
    }
