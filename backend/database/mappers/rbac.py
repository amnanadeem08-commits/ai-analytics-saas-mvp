from __future__ import annotations

from backend.database.models.rbac import PermissionORM, RoleAssignmentORM, RoleORM
from backend.models.rbac_models import Permission, Role, RoleAssignment


def _dump(model) -> dict:
    return model.model_dump(mode="json")


def role_to_orm(role: Role, orm: RoleORM | None = None) -> RoleORM:
    orm = orm or RoleORM()
    orm.role_id = role.role_id
    orm.name = role.name
    orm.scope = role.scope.value if hasattr(role.scope, "value") else str(role.scope)
    orm.created_at = role.created_at
    orm.data = _dump(role)
    return orm


def orm_to_role(orm: RoleORM) -> Role:
    return Role(**orm.data)


def permission_to_orm(perm: Permission, orm: PermissionORM | None = None) -> PermissionORM:
    orm = orm or PermissionORM()
    orm.permission_id = perm.permission_id
    orm.name = perm.name
    orm.scope = perm.scope.value if hasattr(perm.scope, "value") else str(perm.scope)
    orm.data = _dump(perm)
    return orm


def orm_to_permission(orm: PermissionORM) -> Permission:
    return Permission(**orm.data)


def role_assignment_to_orm(assignment: RoleAssignment, orm: RoleAssignmentORM | None = None) -> RoleAssignmentORM:
    orm = orm or RoleAssignmentORM()
    orm.assignment_id = assignment.assignment_id
    orm.user_id = assignment.user_id
    orm.role_id = assignment.role_id
    orm.scope = assignment.scope.value if hasattr(assignment.scope, "value") else str(assignment.scope)
    orm.organization_id = assignment.organization_id
    orm.workspace_id = assignment.workspace_id
    orm.created_at = assignment.created_at
    orm.data = _dump(assignment)
    return orm


def orm_to_role_assignment(orm: RoleAssignmentORM) -> RoleAssignment:
    return RoleAssignment(**orm.data)
