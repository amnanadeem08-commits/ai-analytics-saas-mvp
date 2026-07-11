from __future__ import annotations

import pytest

from backend.storage.config import reset_storage_config
from backend.storage.factory import build_backend, reset_storage_backends
from backend.storage.local_provider import LocalStorageProvider
from backend.storage.metadata import InMemoryStorageMetadataStore
from backend.storage.s3_provider import S3NotConfiguredError, S3StorageProvider


def setup_function():
    reset_storage_config()
    reset_storage_backends()


def test_local_provider_read_write_delete(tmp_path):
    provider = LocalStorageProvider(tmp_path)
    provider.write("a/b.txt", b"data")
    assert provider.read("a/b.txt") == b"data"
    assert provider.exists("a/b.txt")
    assert provider.delete("a/b.txt")
    assert not provider.exists("a/b.txt")


def test_local_provider_list_keys(tmp_path):
    provider = LocalStorageProvider(tmp_path)
    provider.write("prefix/one.bin", b"1")
    provider.write("prefix/two.bin", b"2")
    keys = provider.list_keys("prefix")
    assert "prefix/one.bin" in keys
    assert "prefix/two.bin" in keys


def test_s3_requires_bucket():
    with pytest.raises(S3NotConfiguredError):
        S3StorageProvider(bucket="")


def test_factory_falls_back_to_local_when_s3_misconfigured(monkeypatch):
    monkeypatch.setenv("OBJECT_STORAGE_BACKEND", "s3")
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENV_PROFILE", raising=False)
    reset_storage_config()
    reset_storage_backends()
    backend = build_backend()
    assert isinstance(backend, LocalStorageProvider)


def test_factory_raises_in_production_when_s3_misconfigured(monkeypatch):
    monkeypatch.setenv("OBJECT_STORAGE_BACKEND", "s3")
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    reset_storage_config()
    reset_storage_backends()
    with pytest.raises(Exception):
        build_backend()


def test_metadata_store_find_by_checksum():
    from backend.models.storage_models import ArtifactType, FileChecksum, StorageObject, StorageVersion

    store = InMemoryStorageMetadataStore()
    obj = StorageObject(
        object_id="obj_test",
        name="f.txt",
        artifact_type=ArtifactType.dataset,
        versions=[
            StorageVersion(
                version_id="v1",
                version_number=1,
                checksum=FileChecksum(value="abc123", size_bytes=3),
                is_current=True,
            )
        ],
        current_version=1,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
    )
    store.save(obj)
    found = store.find_by_checksum("abc123")
    assert found is not None
    assert found.object_id == "obj_test"
