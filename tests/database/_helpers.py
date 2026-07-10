from __future__ import annotations

"""Shared helpers to run tests against an in-memory SQLite database."""

import os

from backend.database.config import reset_database_config
from backend.database.database import reset_database
from backend.database.session import dispose_engine


def use_sqlite_memory() -> None:
    """Configure a shared in-memory SQLite database and (re)create the schema."""
    os.environ["STORAGE_BACKEND"] = "postgres"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    reset_database_config()
    dispose_engine()
    reset_database()


def teardown_sqlite() -> None:
    dispose_engine()
    os.environ.pop("DATABASE_URL", None)
    os.environ["STORAGE_BACKEND"] = "memory"
    reset_database_config()
