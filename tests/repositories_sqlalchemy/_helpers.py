from __future__ import annotations

import os

from backend.database.config import reset_database_config
from backend.database.database import reset_database
from backend.database.session import dispose_engine


def use_sqlite_memory() -> None:
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
