from __future__ import annotations

"""KI-009 — durable storage metadata persistence tests."""

from pathlib import Path

import pytest

from backend.database.config import DatabaseConfig, reset_database_config, set_database_config
from backend.database.database import init_database
from backend.database.session import dispose_engine
from backend.models.storage_models import ArtifactType
from backend.services import storage_service
from backend.storage.config import reset_storage_config
from backend.storage.factory import (
    active_metadata_backend,
    build_metadata_store,
    get_metadata_store,
    reset_storage_backends,
)
from backend.storage.file_metadata import FileStorageMetadataStore
from backend.storage.metadata import InMemoryStorageMetadataStore
from backend.storage.migrate import migrate_metadata_store
from backend.repositories.sqlalchemy.storage_repository import SQLAlchemyStorageMetadataStore


@pytest.mark.durable_storage
def test_file_metadata_survives_rebuild(tmp_path: Path, monkeypatch):
    root = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_METADATA_BACKEND", "file")
    monkeypatch.setenv("STORAGE_ROOT_DIR", str(root))
    monkeypatch.setenv("OBJECT_STORAGE_BACKEND", "local")
    reset_storage_config()
    reset_storage_backends()
    storage_service.reset_storage()

    obj = storage_service.upload(
        b"durable-bytes",
        "persist.txt",
        artifact_type=ArtifactType.temporary_upload,
        owner_id="u1",
    )
    object_id = obj.object_id
    assert active_metadata_backend() == "file"

    reset_storage_backends()
    store = get_metadata_store()
    assert isinstance(store, FileStorageMetadataStore)
    loaded = store.get(object_id)
    assert loaded is not None
    assert loaded.name == "persist.txt"
    content, _ = storage_service.download(object_id)
    assert content == b"durable-bytes"


@pytest.mark.durable_storage
def test_sqlalchemy_metadata_survives_rebuild(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "storage_meta.db"
    root = tmp_path / "blobs"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("STORAGE_METADATA_BACKEND", "sqlalchemy")
    monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("STORAGE_ROOT_DIR", str(root))
    monkeypatch.setenv("OBJECT_STORAGE_BACKEND", "local")

    dispose_engine()
    reset_database_config()
    set_database_config(
        DatabaseConfig(storage_backend="sqlite", database_url=url, echo=False)
    )
    dispose_engine()
    init_database()
    reset_storage_config()
    reset_storage_backends()
    storage_service.reset_storage()

    obj = storage_service.upload(
        b"sql-meta",
        "sql.txt",
        artifact_type=ArtifactType.report,
        organization_id="org_1",
    )
    object_id = obj.object_id
    assert active_metadata_backend() == "sqlalchemy"

    reset_storage_backends()
    store = get_metadata_store()
    assert isinstance(store, SQLAlchemyStorageMetadataStore)
    loaded = store.get(object_id)
    assert loaded is not None
    assert loaded.storage_metadata.organization_id == "org_1"

    # cleanup for other tests
    dispose_engine()
    reset_database_config()
    monkeypatch.delenv("STORAGE_METADATA_BACKEND", raising=False)
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    reset_storage_config()
    reset_storage_backends()


@pytest.mark.durable_storage
def test_migrate_metadata_helper(tmp_path: Path):
    source = InMemoryStorageMetadataStore()
    target = FileStorageMetadataStore(tmp_path / "meta.json")

    from backend.models.storage_models import (
        ArtifactType,
        FileChecksum,
        StorageMetadata,
        StorageObject,
        StorageObjectStatus,
        StorageProvider,
        StorageVersion,
    )

    obj = StorageObject(
        object_id="obj_migrate_1",
        name="migrated.bin",
        artifact_type=ArtifactType.temporary_upload,
        provider=StorageProvider.local,
        status=StorageObjectStatus.active,
        current_version=1,
        versions=[
            StorageVersion(
                version_id="v1",
                version_number=1,
                storage_key="k/migrated.bin",
                checksum=FileChecksum(algorithm="sha256", value="deadbeef", size_bytes=4),
                size_bytes=4,
                is_current=True,
            )
        ],
        storage_metadata=StorageMetadata(owner_id="owner"),
        created_at="2026-07-11T00:00:00Z",
        updated_at="2026-07-11T00:00:00Z",
    )
    source.save(obj)
    result = migrate_metadata_store(source, target)
    assert result["copied"] == 1
    assert target.get("obj_migrate_1") is not None
    # idempotent skip
    result2 = migrate_metadata_store(source, target, skip_existing=True)
    assert result2["skipped"] == 1


@pytest.mark.durable_storage
def test_file_to_sql_auto_migration(tmp_path: Path, monkeypatch):
    root = tmp_path / "storage"
    db_path = tmp_path / "auto.db"
    url = f"sqlite:///{db_path.as_posix()}"

    # Seed file index
    monkeypatch.setenv("STORAGE_METADATA_BACKEND", "file")
    monkeypatch.setenv("STORAGE_ROOT_DIR", str(root))
    monkeypatch.setenv("OBJECT_STORAGE_BACKEND", "local")
    reset_storage_config()
    reset_storage_backends()
    storage_service.reset_storage()
    obj = storage_service.upload(b"auto-mig", "auto.txt", artifact_type=ArtifactType.ai_export)
    object_id = obj.object_id

    # Switch to SQL against empty DB — factory should import file index
    dispose_engine()
    reset_database_config()
    set_database_config(DatabaseConfig(storage_backend="sqlite", database_url=url, echo=False))
    dispose_engine()
    init_database()
    monkeypatch.setenv("STORAGE_METADATA_BACKEND", "sqlalchemy")
    monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
    monkeypatch.setenv("DATABASE_URL", url)
    reset_storage_config()
    reset_storage_backends()

    store = build_metadata_store()
    assert isinstance(store, SQLAlchemyStorageMetadataStore)
    loaded = store.get(object_id)
    assert loaded is not None
    assert loaded.name == "auto.txt"

    dispose_engine()
    reset_database_config()
    reset_storage_config()
    reset_storage_backends()
