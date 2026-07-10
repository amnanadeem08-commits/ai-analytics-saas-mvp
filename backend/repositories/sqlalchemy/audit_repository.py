from __future__ import annotations

from backend.database.mappers.audit import audit_event_to_orm, orm_to_audit_event
from backend.database.models.audit import AuthAuditEventORM
from backend.models.user_models import AuthAuditEvent
from backend.repositories.interfaces import AuditRepository
from backend.repositories.sqlalchemy.base import SQLAlchemyRepositoryBase


class SQLAlchemyAuditRepository(SQLAlchemyRepositoryBase, AuditRepository):
    def add(self, event: AuthAuditEvent) -> AuthAuditEvent:
        with self._unit(write=True) as s:
            s.merge(audit_event_to_orm(event))
        return event.model_copy(deep=True)

    def list(
        self,
        *,
        event_type: str | None = None,
        user_id: str | None = None,
        limit: int | None = None,
    ) -> list[AuthAuditEvent]:
        with self._unit() as s:
            query = s.query(AuthAuditEventORM)
            if event_type is not None:
                query = query.filter(AuthAuditEventORM.event_type == event_type)
            if user_id is not None:
                query = query.filter(AuthAuditEventORM.user_id == user_id)
            query = query.order_by(AuthAuditEventORM.timestamp.asc())
            rows = query.all()
            events = [orm_to_audit_event(r) for r in rows]
        if limit is not None:
            events = events[-limit:]
        return events
