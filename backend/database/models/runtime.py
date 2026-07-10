from __future__ import annotations

from typing import Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base, JSONType


class WorkflowExecutionORM(Base):
    __tablename__ = "workflow_executions"

    execution_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="")
    dataset_id: Mapped[str] = mapped_column(String(128), default="")
    started_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class EvaluationRunORM(Base):
    __tablename__ = "evaluation_runs"

    evaluation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    session_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    grade: Mapped[str] = mapped_column(String(4), default="")
    created_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class AnalystSessionORM(Base):
    __tablename__ = "analyst_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="")
    created_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
