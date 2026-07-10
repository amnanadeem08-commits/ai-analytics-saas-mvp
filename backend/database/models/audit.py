from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base, JSONType


class AuthAuditEventORM(Base):
    __tablename__ = "auth_audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, default="")
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    email: Mapped[str] = mapped_column(String(320), default="")
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    timestamp: Mapped[str] = mapped_column(String(40), index=True, default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
