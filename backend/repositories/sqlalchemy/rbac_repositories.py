from __future__ import annotations

from backend.database.mappers.rbac import (
    orm_to_permission,
    orm_to_role,
    orm_to_role_assignment,
    permission_to_orm,
    role_assignment_to_orm,
    role_to_orm,
)
from backend.database.models.rbac import PermissionORM, RoleAssignmentORM, RoleORM
from backend.models.rbac_models import Permission, Role, RoleAssignment
from backend.repositories.interfaces import (
    PermissionRepository,
    RoleAssignmentRepository,
    RoleRepository,
)
from backend.repositories.sqlalchemy.base import SQLAlchemyRepositoryBase


class SQLAlchemyRoleRepository(SQLAlchemyRepositoryBase, RoleRepository):
    def add(self, role: Role) -> Role:
        with self._unit(write=True) as s:
            s.merge(role_to_orm(role))
        return role.model_copy(deep=True)

    def get(self, role_id: str) -> Role | None:
        with self._unit() as s:
            orm = s.get(RoleORM, role_id)
            return orm_to_role(orm) if orm else None

    def update(self, role: Role) -> Role:
        with self._unit(write=True) as s:
            existing = s.get(RoleORM, role.role_id)
            if existing is None:
                raise KeyError(f"Role not found: {role.role_id}")
            role_to_orm(role, existing)
        return role.model_copy(deep=True)

    def list(self) -> list[Role]:
        with self._unit() as s:
            return [orm_to_role(r) for r in s.query(RoleORM).all()]

    def delete(self, role_id: str) -> bool:
        with self._unit(write=True) as s:
            orm = s.get(RoleORM, role_id)
            if orm is None:
                return False
            s.delete(orm)
            return True


class SQLAlchemyPermissionRepository(SQLAlchemyRepositoryBase, PermissionRepository):
    def add(self, permission: Permission) -> Permission:
        with self._unit(write=True) as s:
            s.merge(permission_to_orm(permission))
        return permission.model_copy(deep=True)

    def get(self, permission_id: str) -> Permission | None:
        with self._unit() as s:
            orm = s.get(PermissionORM, permission_id)
            return orm_to_permission(orm) if orm else None

    def list(self) -> list[Permission]:
        with self._unit() as s:
            return [orm_to_permission(r) for r in s.query(PermissionORM).all()]


class SQLAlchemyRoleAssignmentRepository(SQLAlchemyRepositoryBase, RoleAssignmentRepository):
    def add(self, assignment: RoleAssignment) -> RoleAssignment:
        with self._unit(write=True) as s:
            s.merge(role_assignment_to_orm(assignment))
        return assignment.model_copy(deep=True)

    def get(self, assignment_id: str) -> RoleAssignment | None:
        with self._unit() as s:
            orm = s.get(RoleAssignmentORM, assignment_id)
            return orm_to_role_assignment(orm) if orm else None

    def list(
        self,
        *,
        user_id: str | None = None,
        organization_id: str | None = None,
        workspace_id: str | None = None,
    ) -> list[RoleAssignment]:
        with self._unit() as s:
            query = s.query(RoleAssignmentORM)
            if user_id is not None:
                query = query.filter(RoleAssignmentORM.user_id == user_id)
            if organization_id is not None:
                query = query.filter(RoleAssignmentORM.organization_id == organization_id)
            if workspace_id is not None:
                query = query.filter(RoleAssignmentORM.workspace_id == workspace_id)
            return [orm_to_role_assignment(r) for r in query.all()]

    def delete(self, assignment_id: str) -> bool:
        with self._unit(write=True) as s:
            orm = s.get(RoleAssignmentORM, assignment_id)
            if orm is None:
                return False
            s.delete(orm)
            return True
