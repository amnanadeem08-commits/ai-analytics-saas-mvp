from __future__ import annotations

from backend.database.mappers.organization import (
    invitation_to_orm,
    member_to_orm,
    orm_to_invitation,
    orm_to_member,
    orm_to_organization,
    orm_to_workspace,
    organization_to_orm,
    workspace_to_orm,
)
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
from backend.repositories.interfaces import (
    InvitationRepository,
    MembershipRepository,
    OrganizationRepository,
    WorkspaceRepository,
)
from backend.repositories.sqlalchemy.base import SQLAlchemyRepositoryBase


class SQLAlchemyOrganizationRepository(SQLAlchemyRepositoryBase, OrganizationRepository):
    def add(self, organization: Organization) -> Organization:
        with self._unit(write=True) as s:
            s.merge(organization_to_orm(organization))
        return organization.model_copy(deep=True)

    def get(self, organization_id: str) -> Organization | None:
        with self._unit() as s:
            orm = s.get(OrganizationORM, organization_id)
            return orm_to_organization(orm) if orm else None

    def get_by_slug(self, slug: str) -> Organization | None:
        with self._unit() as s:
            orm = s.query(OrganizationORM).filter(OrganizationORM.slug == slug).first()
            return orm_to_organization(orm) if orm else None

    def update(self, organization: Organization) -> Organization:
        with self._unit(write=True) as s:
            existing = s.get(OrganizationORM, organization.organization_id)
            if existing is None:
                raise KeyError(f"Organization not found: {organization.organization_id}")
            organization_to_orm(organization, existing)
        return organization.model_copy(deep=True)

    def list(self, *, owner_id: str | None = None, include_archived: bool = True) -> list[Organization]:
        with self._unit() as s:
            query = s.query(OrganizationORM)
            if owner_id is not None:
                query = query.filter(OrganizationORM.owner_id == owner_id)
            if not include_archived:
                query = query.filter(OrganizationORM.status != "archived")
            rows = query.all()
            result = [orm_to_organization(r) for r in rows]
        result.sort(key=lambda o: o.created_at)
        return result

    def delete(self, organization_id: str) -> bool:
        with self._unit(write=True) as s:
            orm = s.get(OrganizationORM, organization_id)
            if orm is None:
                return False
            s.delete(orm)
            return True


class SQLAlchemyWorkspaceRepository(SQLAlchemyRepositoryBase, WorkspaceRepository):
    def add(self, workspace: Workspace) -> Workspace:
        with self._unit(write=True) as s:
            s.merge(workspace_to_orm(workspace))
        return workspace.model_copy(deep=True)

    def get(self, workspace_id: str) -> Workspace | None:
        with self._unit() as s:
            orm = s.get(WorkspaceORM, workspace_id)
            return orm_to_workspace(orm) if orm else None

    def update(self, workspace: Workspace) -> Workspace:
        with self._unit(write=True) as s:
            existing = s.get(WorkspaceORM, workspace.workspace_id)
            if existing is None:
                raise KeyError(f"Workspace not found: {workspace.workspace_id}")
            workspace_to_orm(workspace, existing)
        return workspace.model_copy(deep=True)

    def list(self, *, organization_id: str | None = None, include_archived: bool = True) -> list[Workspace]:
        with self._unit() as s:
            query = s.query(WorkspaceORM)
            if organization_id is not None:
                query = query.filter(WorkspaceORM.organization_id == organization_id)
            if not include_archived:
                query = query.filter(WorkspaceORM.status != "archived")
            rows = query.all()
            result = [orm_to_workspace(r) for r in rows]
        result.sort(key=lambda w: w.created_at)
        return result

    def delete(self, workspace_id: str) -> bool:
        with self._unit(write=True) as s:
            orm = s.get(WorkspaceORM, workspace_id)
            if orm is None:
                return False
            s.delete(orm)
            return True


class SQLAlchemyMembershipRepository(SQLAlchemyRepositoryBase, MembershipRepository):
    def add(self, member: OrganizationMember) -> OrganizationMember:
        with self._unit(write=True) as s:
            s.merge(member_to_orm(member))
        return member.model_copy(deep=True)

    def get(self, member_id: str) -> OrganizationMember | None:
        with self._unit() as s:
            orm = s.get(OrganizationMemberORM, member_id)
            return orm_to_member(orm) if orm else None

    def find(self, *, organization_id: str, user_id: str) -> OrganizationMember | None:
        with self._unit() as s:
            orm = (
                s.query(OrganizationMemberORM)
                .filter(
                    OrganizationMemberORM.organization_id == organization_id,
                    OrganizationMemberORM.user_id == user_id,
                )
                .first()
            )
            return orm_to_member(orm) if orm else None

    def update(self, member: OrganizationMember) -> OrganizationMember:
        with self._unit(write=True) as s:
            existing = s.get(OrganizationMemberORM, member.member_id)
            if existing is None:
                raise KeyError(f"Member not found: {member.member_id}")
            member_to_orm(member, existing)
        return member.model_copy(deep=True)

    def list(self, *, organization_id: str | None = None, user_id: str | None = None) -> list[OrganizationMember]:
        with self._unit() as s:
            query = s.query(OrganizationMemberORM)
            if organization_id is not None:
                query = query.filter(OrganizationMemberORM.organization_id == organization_id)
            if user_id is not None:
                query = query.filter(OrganizationMemberORM.user_id == user_id)
            rows = query.all()
            result = [orm_to_member(r) for r in rows]
        result.sort(key=lambda m: m.created_at)
        return result

    def delete(self, member_id: str) -> bool:
        with self._unit(write=True) as s:
            orm = s.get(OrganizationMemberORM, member_id)
            if orm is None:
                return False
            s.delete(orm)
            return True


class SQLAlchemyInvitationRepository(SQLAlchemyRepositoryBase, InvitationRepository):
    def add(self, invitation: Invitation) -> Invitation:
        with self._unit(write=True) as s:
            s.merge(invitation_to_orm(invitation))
        return invitation.model_copy(deep=True)

    def get(self, invitation_id: str) -> Invitation | None:
        with self._unit() as s:
            orm = s.get(InvitationORM, invitation_id)
            return orm_to_invitation(orm) if orm else None

    def find_by_token_hash(self, token_hash: str) -> Invitation | None:
        with self._unit() as s:
            orm = s.query(InvitationORM).filter(InvitationORM.token_hash == token_hash).first()
            return orm_to_invitation(orm) if orm else None

    def update(self, invitation: Invitation) -> Invitation:
        with self._unit(write=True) as s:
            existing = s.get(InvitationORM, invitation.invitation_id)
            if existing is None:
                raise KeyError(f"Invitation not found: {invitation.invitation_id}")
            invitation_to_orm(invitation, existing)
        return invitation.model_copy(deep=True)

    def list(self, *, organization_id: str | None = None, email: str | None = None) -> list[Invitation]:
        with self._unit() as s:
            query = s.query(InvitationORM)
            if organization_id is not None:
                query = query.filter(InvitationORM.organization_id == organization_id)
            if email is not None:
                query = query.filter(InvitationORM.email == email)
            rows = query.all()
            result = [orm_to_invitation(r) for r in rows]
        result.sort(key=lambda i: i.created_at)
        return result
