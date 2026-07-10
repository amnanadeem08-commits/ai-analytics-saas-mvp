from __future__ import annotations

"""SQLAlchemy declarative base + shared column helpers (Sprint 8.2)."""

from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# Portable JSON type: SQLAlchemy maps this to JSONB on PostgreSQL and TEXT-backed
# JSON on SQLite automatically via the generic JSON type.
JSONType = JSON
