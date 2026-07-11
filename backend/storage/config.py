from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _resolve_object_backend() -> str:
    """Prefer OBJECT_STORAGE_BACKEND; avoid colliding with DB STORAGE_BACKEND values."""
    explicit = os.getenv("OBJECT_STORAGE_BACKEND", "").strip().lower()
    if explicit:
        return explicit
    raw = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    if raw in {"local", "s3", "aws"}:
        return raw
    # STORAGE_BACKEND may be memory/sqlite/postgres for DB — keep files local.
    return "local"


@dataclass
class StorageConfig:
    """Environment-driven object storage configuration."""

    backend: str = field(default_factory=_resolve_object_backend)
    root_dir: Path = field(
        default_factory=lambda: Path(os.getenv("STORAGE_ROOT_DIR", "")).expanduser()
        if os.getenv("STORAGE_ROOT_DIR")
        else Path(__file__).resolve().parents[2] / "data" / "storage"
    )
    namespace: str = field(default_factory=lambda: os.getenv("STORAGE_NAMESPACE", "databot"))
    s3_bucket: str = field(default_factory=lambda: os.getenv("S3_BUCKET", ""))
    s3_endpoint: str = field(default_factory=lambda: os.getenv("S3_ENDPOINT", ""))
    s3_region: str = field(default_factory=lambda: os.getenv("S3_REGION", "us-east-1"))
    quota_bytes: int = field(default_factory=lambda: _int_env("STORAGE_QUOTA_BYTES", 10 * 1024 * 1024 * 1024))
    default_max_versions: int = field(default_factory=lambda: _int_env("STORAGE_MAX_VERSIONS", 10))

    @property
    def uses_s3(self) -> bool:
        return self.backend in {"s3", "aws"}


_CONFIG: StorageConfig | None = None


def get_storage_config(*, refresh: bool = False) -> StorageConfig:
    global _CONFIG
    if _CONFIG is None or refresh:
        _CONFIG = StorageConfig()
    return _CONFIG


def reset_storage_config() -> None:
    global _CONFIG
    _CONFIG = None
