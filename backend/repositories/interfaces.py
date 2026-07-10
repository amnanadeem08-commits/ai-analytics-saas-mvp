from __future__ import annotations

"""Abstract repository interfaces. Business logic depends only on these."""

from abc import ABC, abstractmethod

from backend.models.organization_models import (
    Invitation,
    Organization,
    OrganizationMember,
    Workspace,
)
from backend.models.rbac_models import Permission, Role, RoleAssignment
from backend.models.user_models import AuthAuditEvent


class OrganizationRepository(ABC):
    @abstractmethod
    def add(self, organization: Organization) -> Organization: ...

    @abstractmethod
    def get(self, organization_id: str) -> Organization | None: ...

    @abstractmethod
    def get_by_slug(self, slug: str) -> Organization | None: ...

    @abstractmethod
    def update(self, organization: Organization) -> Organization: ...

    @abstractmethod
    def list(self, *, owner_id: str | None = None, include_archived: bool = True) -> list[Organization]: ...

    @abstractmethod
    def delete(self, organization_id: str) -> bool: ...


class WorkspaceRepository(ABC):
    @abstractmethod
    def add(self, workspace: Workspace) -> Workspace: ...

    @abstractmethod
    def get(self, workspace_id: str) -> Workspace | None: ...

    @abstractmethod
    def update(self, workspace: Workspace) -> Workspace: ...

    @abstractmethod
    def list(self, *, organization_id: str | None = None, include_archived: bool = True) -> list[Workspace]: ...

    @abstractmethod
    def delete(self, workspace_id: str) -> bool: ...


class MembershipRepository(ABC):
    @abstractmethod
    def add(self, member: OrganizationMember) -> OrganizationMember: ...

    @abstractmethod
    def get(self, member_id: str) -> OrganizationMember | None: ...

    @abstractmethod
    def find(self, *, organization_id: str, user_id: str) -> OrganizationMember | None: ...

    @abstractmethod
    def update(self, member: OrganizationMember) -> OrganizationMember: ...

    @abstractmethod
    def list(self, *, organization_id: str | None = None, user_id: str | None = None) -> list[OrganizationMember]: ...

    @abstractmethod
    def delete(self, member_id: str) -> bool: ...


class RoleRepository(ABC):
    @abstractmethod
    def add(self, role: Role) -> Role: ...

    @abstractmethod
    def get(self, role_id: str) -> Role | None: ...

    @abstractmethod
    def update(self, role: Role) -> Role: ...

    @abstractmethod
    def list(self) -> list[Role]: ...

    @abstractmethod
    def delete(self, role_id: str) -> bool: ...


class PermissionRepository(ABC):
    @abstractmethod
    def add(self, permission: Permission) -> Permission: ...

    @abstractmethod
    def get(self, permission_id: str) -> Permission | None: ...

    @abstractmethod
    def list(self) -> list[Permission]: ...


class RoleAssignmentRepository(ABC):
    @abstractmethod
    def add(self, assignment: RoleAssignment) -> RoleAssignment: ...

    @abstractmethod
    def get(self, assignment_id: str) -> RoleAssignment | None: ...

    @abstractmethod
    def list(
        self,
        *,
        user_id: str | None = None,
        organization_id: str | None = None,
        workspace_id: str | None = None,
    ) -> list[RoleAssignment]: ...

    @abstractmethod
    def delete(self, assignment_id: str) -> bool: ...


class InvitationRepository(ABC):
    @abstractmethod
    def add(self, invitation: Invitation) -> Invitation: ...

    @abstractmethod
    def get(self, invitation_id: str) -> Invitation | None: ...

    @abstractmethod
    def find_by_token_hash(self, token_hash: str) -> Invitation | None: ...

    @abstractmethod
    def update(self, invitation: Invitation) -> Invitation: ...

    @abstractmethod
    def list(self, *, organization_id: str | None = None, email: str | None = None) -> list[Invitation]: ...


class AuditRepository(ABC):
    @abstractmethod
    def add(self, event: AuthAuditEvent) -> AuthAuditEvent: ...

    @abstractmethod
    def list(
        self,
        *,
        event_type: str | None = None,
        user_id: str | None = None,
        limit: int | None = None,
    ) -> list[AuthAuditEvent]: ...
