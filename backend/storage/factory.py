from __future__ import annotations

"""Storage provider factory with configuration-driven selection + safe fallback."""

import logging
import os

from backend.storage.config import get_storage_config
from backend.storage.interfaces import StorageBackend, StorageMetadataStore
from backend.storage.local_provider import LocalStorageProvider
from backend.storage.metadata import InMemoryStorageMetadataStore

_log = logging.getLogger("ai_analytics.storage")

_backend: StorageBackend | None = None
_metadata: StorageMetadataStore | None = None
_active_provider: str = "local"
_active_metadata_backend: str = "memory"


def _is_production() -> bool:
    profile = (
        os.getenv("ENV_PROFILE")
        or os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or ""
    ).strip().lower()
    return profile in {"production", "prod"}


def _resolve_metadata_backend() -> str:
    """Select durable metadata backend (KI-009).

    Priority:
    1. STORAGE_METADATA_BACKEND env (memory | file | sqlite | postgres | sqlalchemy)
    2. Database config when SQL is enabled
    3. file (durable JSON under STORAGE_ROOT_DIR) — default, survives restarts
    """
    explicit = os.getenv("STORAGE_METADATA_BACKEND", "").strip().lower()
    if explicit in {"memory", "mem", "local-memory"}:
        return "memory"
    if explicit in {"file", "json", "fs"}:
        return "file"
    if explicit in {"postgres", "postgresql", "sqlite", "sqlalchemy", "database", "sql"}:
        return "sqlalchemy"
    try:
        from backend.database.config import get_database_config

        if get_database_config().uses_database:
            return "sqlalchemy"
    except Exception as exc:  # noqa: BLE001
        _log.debug("Database config unavailable for metadata backend selection: %s", exc)
    return "file"


def _file_metadata_path():
    config = get_storage_config()
    return config.root_dir / "metadata_index.json"


def _build_file_metadata_store() -> StorageMetadataStore:
    from backend.storage.file_metadata import FileStorageMetadataStore

    path = _file_metadata_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return FileStorageMetadataStore(path)


def _build_sql_metadata_store() -> StorageMetadataStore:
    from backend.database.database import init_database
    from backend.repositories.sqlalchemy.storage_repository import SQLAlchemyStorageMetadataStore
    from backend.storage.migrate import migrate_metadata_store

    init_database()
    store = SQLAlchemyStorageMetadataStore()
    # Automatic migration: import file index when SQL catalog is empty.
    try:
        if not store.list():
            file_path = _file_metadata_path()
            if file_path.exists():
                file_store = _build_file_metadata_store()
                if file_store.list():
                    result = migrate_metadata_store(file_store, store)
                    _log.info("Migrated storage metadata from file → SQL: %s", result)
    except Exception as exc:  # noqa: BLE001
        _log.warning("Automatic file→SQL metadata migration skipped: %s", exc)
    return store


def build_backend() -> StorageBackend:
    config = get_storage_config()
    if config.uses_s3:
        try:
            from backend.storage.s3_provider import S3StorageProvider

            return S3StorageProvider(
                bucket=config.s3_bucket,
                endpoint=config.s3_endpoint,
                region=config.s3_region,
            )
        except Exception as exc:  # noqa: BLE001
            if _is_production():
                _log.error("S3 storage required in production but unavailable: %s", exc)
                raise
            _log.warning("S3 storage unavailable (%s); falling back to local provider.", exc)
    config.root_dir.mkdir(parents=True, exist_ok=True)
    return LocalStorageProvider(config.root_dir)


def build_metadata_store() -> StorageMetadataStore:
    global _active_metadata_backend
    backend = _resolve_metadata_backend()
    if backend == "memory":
        _active_metadata_backend = "memory"
        return InMemoryStorageMetadataStore()
    if backend == "sqlalchemy":
        try:
            store = _build_sql_metadata_store()
            _active_metadata_backend = "sqlalchemy"
            return store
        except Exception as exc:  # noqa: BLE001
            if _is_production():
                _log.error("SQL storage metadata required but unavailable: %s", exc)
                raise
            _log.warning("SQL storage metadata unavailable (%s); falling back to file store.", exc)
    _active_metadata_backend = "file"
    return _build_file_metadata_store()


def get_backend() -> StorageBackend:
    global _backend, _active_provider
    if _backend is None:
        _backend = build_backend()
        _active_provider = getattr(_backend, "provider_name", "local")
    return _backend


def get_metadata_store() -> StorageMetadataStore:
    global _metadata
    if _metadata is None:
        _metadata = build_metadata_store()
    return _metadata


def active_provider() -> str:
    get_backend()
    return _active_provider


def active_metadata_backend() -> str:
    get_metadata_store()
    return _active_metadata_backend


def reset_storage_backends() -> None:
    """Test helper — rebuild backend + metadata store from current configuration."""
    global _backend, _metadata, _active_provider, _active_metadata_backend
    _backend = None
    _metadata = None
    _active_provider = "local"
    _active_metadata_backend = "memory"
