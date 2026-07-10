from __future__ import annotations

from backend.database.models.audit import AuthAuditEventORM
from backend.models.user_models import AuthAuditEvent


def audit_event_to_orm(event: AuthAuditEvent, orm: AuthAuditEventORM | None = None) -> AuthAuditEventORM:
    orm = orm or AuthAuditEventORM()
    orm.event_id = event.event_id
    orm.event_type = event.event_type
    orm.user_id = event.user_id
    orm.email = event.email
    orm.success = event.success
    orm.timestamp = event.timestamp
    orm.data = event.model_dump(mode="json")
    return orm


def orm_to_audit_event(orm: AuthAuditEventORM) -> AuthAuditEvent:
    return AuthAuditEvent(**orm.data)
