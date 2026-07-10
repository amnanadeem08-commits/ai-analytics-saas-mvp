from __future__ import annotations

"""Database configuration (Sprint 8.2).

All values are environment-driven. Supports SQLite (development) and
PostgreSQL (production) selected entirely from configuration.
"""

import os
from dataclasses import dataclass, field


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Default local-first SQLite database file lives under the data directory.
_DEFAULT_SQLITE_URL = "sqlite:///./data/app.db"


@dataclass
class DatabaseConfig:
    """Resolved database configuration."""

    storage_backend: str = field(default_factory=lambda: os.getenv("STORAGE_BACKEND", "memory").strip().lower())
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", _DEFAULT_SQLITE_URL))
    echo: bool = field(default_factory=lambda: _bool_env("SQLALCHEMY_ECHO", False))
    pool_size: int = field(default_factory=lambda: _int_env("POOL_SIZE", 5))
    pool_timeout: int = field(default_factory=lambda: _int_env("POOL_TIMEOUT", 30))
    max_overflow: int = field(default_factory=lambda: _int_env("MAX_OVERFLOW", 10))

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgres")

    @property
    def is_memory_sqlite(self) -> bool:
        return self.is_sqlite and (":memory:" in self.database_url)

    @property
    def uses_database(self) -> bool:
        """True when a persistent (SQLAlchemy) backend is selected."""
        return self.storage_backend in {"postgres", "postgresql", "sqlite", "sqlalchemy", "database"}


_CONFIG: DatabaseConfig | None = None


def get_database_config(*, refresh: bool = False) -> DatabaseConfig:
    global _CONFIG
    if _CONFIG is None or refresh:
        _CONFIG = DatabaseConfig()
    return _CONFIG


def set_database_config(config: DatabaseConfig) -> DatabaseConfig:
    global _CONFIG
    _CONFIG = config
    return _CONFIG


def reset_database_config() -> None:
    global _CONFIG
    _CONFIG = None
