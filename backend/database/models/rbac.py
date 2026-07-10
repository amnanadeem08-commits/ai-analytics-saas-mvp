from __future__ import annotations

from typing import Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base, JSONType


class RoleORM(Base):
    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    scope: Mapped[str] = mapped_column(String(32), index=True, default="organization")
    created_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class PermissionORM(Base):
    __tablename__ = "permissions"

    permission_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    scope: Mapped[str] = mapped_column(String(32), index=True, default="organization")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class RoleAssignmentORM(Base):
    __tablename__ = "role_assignments"

    assignment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    role_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    scope: Mapped[str] = mapped_column(String(32), index=True, default="organization")
    organization_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    created_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
