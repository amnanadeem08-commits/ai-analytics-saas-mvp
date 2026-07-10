from __future__ import annotations

"""ORM <-> domain mappers (Sprint 8.2).

The Pydantic domain model is the source of truth: the full object is stored in
the ORM ``data`` JSON column, while indexed columns mirror queryable fields.
Repositories use these mappers; services never import ORM classes.
"""

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
from backend.database.mappers.rbac import (
    orm_to_permission,
    orm_to_role,
    orm_to_role_assignment,
    permission_to_orm,
    role_assignment_to_orm,
    role_to_orm,
)
from backend.database.mappers.audit import audit_event_to_orm, orm_to_audit_event

__all__ = [
    "organization_to_orm",
    "orm_to_organization",
    "workspace_to_orm",
    "orm_to_workspace",
    "member_to_orm",
    "orm_to_member",
    "invitation_to_orm",
    "orm_to_invitation",
    "role_to_orm",
    "orm_to_role",
    "permission_to_orm",
    "orm_to_permission",
    "role_assignment_to_orm",
    "orm_to_role_assignment",
    "audit_event_to_orm",
    "orm_to_audit_event",
]
