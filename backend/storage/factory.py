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


def _is_production() -> bool:
    profile = (
        os.getenv("ENV_PROFILE")
        or os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or ""
    ).strip().lower()
    return profile in {"production", "prod"}


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
    return InMemoryStorageMetadataStore()


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


def reset_storage_backends() -> None:
    """Test helper — rebuild backend + metadata store from current configuration."""
    global _backend, _metadata, _active_provider
    _backend = None
    _metadata = None
    _active_provider = "local"
