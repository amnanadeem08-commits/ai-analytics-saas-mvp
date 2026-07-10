from __future__ import annotations

"""Database bootstrap + health check (Sprint 8.2)."""

from typing import Any

from sqlalchemy import text

from backend.database.base import Base
from backend.database.config import get_database_config
from backend.database.session import dispose_engine, get_engine, session_scope

# Importing the models package registers all ORM tables on Base.metadata.
import backend.database.models  # noqa: F401


def init_database() -> None:
    """Create all tables for the configured database (idempotent)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_all() -> None:
    """Drop all tables (test helper)."""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)


def reset_database() -> None:
    """Drop + recreate all tables (test helper)."""
    drop_all()
    init_database()


def health_check() -> dict[str, Any]:
    """Return a database health probe result."""
    config = get_database_config()
    status: dict[str, Any] = {
        "backend": config.storage_backend,
        "dialect": "sqlite" if config.is_sqlite else ("postgresql" if config.is_postgres else "other"),
        "connected": False,
        "error": "",
    }
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
        status["connected"] = True
    except Exception as exc:  # noqa: BLE001
        status["error"] = str(exc)
    return status
