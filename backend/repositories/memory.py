from __future__ import annotations

"""In-memory repository implementations (Sprint 8.1).

Deterministic, dependency-free storage suitable for tests and local dev.
Sprint 8.2 can replace these with persistent backends behind the same
interfaces without touching services.
"""

from backend.models.organization_models import (
    Invitation,
    Organization,
    OrganizationMember,
    Workspace,
)
from backend.models.rbac_models import Permission, Role, RoleAssignment
from backend.models.user_models import AuthAuditEvent
from backend.repositories.interfaces import (
    AuditRepository,
    InvitationRepository,
    MembershipRepository,
    OrganizationRepository,
    PermissionRepository,
    RoleAssignmentRepository,
    RoleRepository,
    WorkspaceRepository,
)


class InMemoryOrganizationRepository(OrganizationRepository):
    def __init__(self) -> None:
        self._items: dict[str, Organization] = {}

    def add(self, organization: Organization) -> Organization:
        self._items[organization.organization_id] = organization.model_copy(deep=True)
        return organization.model_copy(deep=True)

    def get(self, organization_id: str) -> Organization | None:
        item = self._items.get(organization_id)
        return item.model_copy(deep=True) if item else None

    def get_by_slug(self, slug: str) -> Organization | None:
        for item in self._items.values():
            if item.slug and item.slug == slug:
                return item.model_copy(deep=True)
        return None

    def update(self, organization: Organization) -> Organization:
        if organization.organization_id not in self._items:
            raise KeyError(f"Organization not found: {organization.organization_id}")
        self._items[organization.organization_id] = organization.model_copy(deep=True)
        return organization.model_copy(deep=True)

    def list(self, *, owner_id: str | None = None, include_archived: bool = True) -> list[Organization]:
        results = []
        for item in self._items.values():
            if owner_id is not None and item.owner_id != owner_id:
                continue
            if not include_archived and item.status.value == "archived":
                continue
            results.append(item.model_copy(deep=True))
        results.sort(key=lambda o: o.created_at)
        return results

    def delete(self, organization_id: str) -> bool:
        return self._items.pop(organization_id, None) is not None


class InMemoryWorkspaceRepository(WorkspaceRepository):
    def __init__(self) -> None:
        self._items: dict[str, Workspace] = {}

    def add(self, workspace: Workspace) -> Workspace:
        self._items[workspace.workspace_id] = workspace.model_copy(deep=True)
        return workspace.model_copy(deep=True)

    def get(self, workspace_id: str) -> Workspace | None:
        item = self._items.get(workspace_id)
        return item.model_copy(deep=True) if item else None

    def update(self, workspace: Workspace) -> Workspace:
        if workspace.workspace_id not in self._items:
            raise KeyError(f"Workspace not found: {workspace.workspace_id}")
        self._items[workspace.workspace_id] = workspace.model_copy(deep=True)
        return workspace.model_copy(deep=True)

    def list(self, *, organization_id: str | None = None, include_archived: bool = True) -> list[Workspace]:
        results = []
        for item in self._items.values():
            if organization_id is not None and item.organization_id != organization_id:
                continue
            if not include_archived and item.status.value == "archived":
                continue
            results.append(item.model_copy(deep=True))
        results.sort(key=lambda w: w.created_at)
        return results

    def delete(self, workspace_id: str) -> bool:
        return self._items.pop(workspace_id, None) is not None


class InMemoryMembershipRepository(MembershipRepository):
    def __init__(self) -> None:
        self._items: dict[str, OrganizationMember] = {}

    def add(self, member: OrganizationMember) -> OrganizationMember:
        self._items[member.member_id] = member.model_copy(deep=True)
        return member.model_copy(deep=True)

    def get(self, member_id: str) -> OrganizationMember | None:
        item = self._items.get(member_id)
        return item.model_copy(deep=True) if item else None

    def find(self, *, organization_id: str, user_id: str) -> OrganizationMember | None:
        for item in self._items.values():
            if item.organization_id == organization_id and item.user_id == user_id:
                return item.model_copy(deep=True)
        return None

    def update(self, member: OrganizationMember) -> OrganizationMember:
        if member.member_id not in self._items:
            raise KeyError(f"Member not found: {member.member_id}")
        self._items[member.member_id] = member.model_copy(deep=True)
        return member.model_copy(deep=True)

    def list(self, *, organization_id: str | None = None, user_id: str | None = None) -> list[OrganizationMember]:
        results = []
        for item in self._items.values():
            if organization_id is not None and item.organization_id != organization_id:
                continue
            if user_id is not None and item.user_id != user_id:
                continue
            results.append(item.model_copy(deep=True))
        results.sort(key=lambda m: m.created_at)
        return results

    def delete(self, member_id: str) -> bool:
        return self._items.pop(member_id, None) is not None


class InMemoryRoleRepository(RoleRepository):
    def __init__(self) -> None:
        self._items: dict[str, Role] = {}

    def add(self, role: Role) -> Role:
        self._items[role.role_id] = role.model_copy(deep=True)
        return role.model_copy(deep=True)

    def get(self, role_id: str) -> Role | None:
        item = self._items.get(role_id)
        return item.model_copy(deep=True) if item else None

    def update(self, role: Role) -> Role:
        if role.role_id not in self._items:
            raise KeyError(f"Role not found: {role.role_id}")
        self._items[role.role_id] = role.model_copy(deep=True)
        return role.model_copy(deep=True)

    def list(self) -> list[Role]:
        return [r.model_copy(deep=True) for r in self._items.values()]

    def delete(self, role_id: str) -> bool:
        return self._items.pop(role_id, None) is not None


class InMemoryPermissionRepository(PermissionRepository):
    def __init__(self) -> None:
        self._items: dict[str, Permission] = {}

    def add(self, permission: Permission) -> Permission:
        self._items[permission.permission_id] = permission.model_copy(deep=True)
        return permission.model_copy(deep=True)

    def get(self, permission_id: str) -> Permission | None:
        item = self._items.get(permission_id)
        return item.model_copy(deep=True) if item else None

    def list(self) -> list[Permission]:
        return [p.model_copy(deep=True) for p in self._items.values()]


class InMemoryRoleAssignmentRepository(RoleAssignmentRepository):
    def __init__(self) -> None:
        self._items: dict[str, RoleAssignment] = {}

    def add(self, assignment: RoleAssignment) -> RoleAssignment:
        self._items[assignment.assignment_id] = assignment.model_copy(deep=True)
        return assignment.model_copy(deep=True)

    def get(self, assignment_id: str) -> RoleAssignment | None:
        item = self._items.get(assignment_id)
        return item.model_copy(deep=True) if item else None

    def list(
        self,
        *,
        user_id: str | None = None,
        organization_id: str | None = None,
        workspace_id: str | None = None,
    ) -> list[RoleAssignment]:
        results = []
        for item in self._items.values():
            if user_id is not None and item.user_id != user_id:
                continue
            if organization_id is not None and item.organization_id != organization_id:
                continue
            if workspace_id is not None and item.workspace_id != workspace_id:
                continue
            results.append(item.model_copy(deep=True))
        return results

    def delete(self, assignment_id: str) -> bool:
        return self._items.pop(assignment_id, None) is not None


class InMemoryInvitationRepository(InvitationRepository):
    def __init__(self) -> None:
        self._items: dict[str, Invitation] = {}

    def add(self, invitation: Invitation) -> Invitation:
        self._items[invitation.invitation_id] = invitation.model_copy(deep=True)
        return invitation.model_copy(deep=True)

    def get(self, invitation_id: str) -> Invitation | None:
        item = self._items.get(invitation_id)
        return item.model_copy(deep=True) if item else None

    def find_by_token_hash(self, token_hash: str) -> Invitation | None:
        for item in self._items.values():
            if item.token_hash and item.token_hash == token_hash:
                return item.model_copy(deep=True)
        return None

    def update(self, invitation: Invitation) -> Invitation:
        if invitation.invitation_id not in self._items:
            raise KeyError(f"Invitation not found: {invitation.invitation_id}")
        self._items[invitation.invitation_id] = invitation.model_copy(deep=True)
        return invitation.model_copy(deep=True)

    def list(self, *, organization_id: str | None = None, email: str | None = None) -> list[Invitation]:
        results = []
        for item in self._items.values():
            if organization_id is not None and item.organization_id != organization_id:
                continue
            if email is not None and item.email != email:
                continue
            results.append(item.model_copy(deep=True))
        results.sort(key=lambda i: i.created_at)
        return results


class InMemoryAuditRepository(AuditRepository):
    def __init__(self) -> None:
        self._items: list[AuthAuditEvent] = []

    def add(self, event: AuthAuditEvent) -> AuthAuditEvent:
        self._items.append(event.model_copy(deep=True))
        return event.model_copy(deep=True)

    def list(
        self,
        *,
        event_type: str | None = None,
        user_id: str | None = None,
        limit: int | None = None,
    ) -> list[AuthAuditEvent]:
        results = []
        for item in self._items:
            if event_type is not None and item.event_type != event_type:
                continue
            if user_id is not None and item.user_id != user_id:
                continue
            results.append(item.model_copy(deep=True))
        if limit is not None:
            results = results[-limit:]
        return results
