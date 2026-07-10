from __future__ import annotations

"""Storage subsystem (Sprint 8.4)."""

from backend.storage.config import get_storage_config, reset_storage_config
from backend.storage.factory import (
    active_provider,
    build_backend,
    build_metadata_store,
    get_backend,
    get_metadata_store,
    reset_storage_backends,
)
from backend.storage.interfaces import StorageBackend, StorageMetadataStore

__all__ = [
    "StorageBackend",
    "StorageMetadataStore",
    "get_storage_config",
    "reset_storage_config",
    "get_backend",
    "get_metadata_store",
    "build_backend",
    "build_metadata_store",
    "active_provider",
    "reset_storage_backends",
]
