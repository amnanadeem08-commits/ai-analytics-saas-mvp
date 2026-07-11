from __future__ import annotations

"""ORM model for durable StorageObject metadata (KI-009 / TD-011)."""

from typing import Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base, JSONType


class StorageObjectORM(Base):
    """Indexed identity/filter columns + full StorageObject JSON payload."""

    __tablename__ = "storage_objects"

    object_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), default="")
    artifact_type: Mapped[str] = mapped_column(String(64), index=True, default="")
    provider: Mapped[str] = mapped_column(String(32), default="local")
    status: Mapped[str] = mapped_column(String(32), index=True, default="active")
    owner_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    organization_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    current_checksum: Mapped[str] = mapped_column(String(128), index=True, default="")
    created_at: Mapped[str] = mapped_column(String(40), index=True, default="")
    updated_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
