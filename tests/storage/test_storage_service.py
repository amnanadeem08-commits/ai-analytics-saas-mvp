from __future__ import annotations

import pytest

from backend.models.storage_models import ArtifactType, StorageObjectStatus
from backend.services import storage_service
from backend.storage.factory import reset_storage_backends


def setup_function():
    storage_service.reset_storage()


def test_upload_download_roundtrip():
    obj = storage_service.upload(
        b"hello storage",
        "hello.txt",
        artifact_type=ArtifactType.temporary_upload,
        owner_id="user_1",
    )
    content, reloaded = storage_service.download(obj.object_id)
    assert content == b"hello storage"
    assert reloaded.object_id == obj.object_id
    assert reloaded.current_version == 1


def test_versioning_appends_not_overwrites():
    first = storage_service.upload(b"v1", "doc.txt", artifact_type=ArtifactType.report)
    second = storage_service.upload(
        b"v2",
        "doc.txt",
        artifact_type=ArtifactType.report,
        object_id=first.object_id,
    )
    assert second.current_version == 2
    assert len(second.versions) == 2
    c1, _ = storage_service.download(first.object_id, version_number=1)
    c2, _ = storage_service.download(first.object_id, version_number=2)
    assert c1 == b"v1"
    assert c2 == b"v2"


def test_rollback_sets_current_version():
    obj = storage_service.upload(b"a", "a.txt", artifact_type=ArtifactType.ai_export)
    storage_service.upload(b"b", "a.txt", artifact_type=ArtifactType.ai_export, object_id=obj.object_id)
    rolled = storage_service.rollback_version(obj.object_id, 1)
    assert rolled.current_version == 1
    content, _ = storage_service.download(obj.object_id)
    assert content == b"a"


def test_checksum_verification():
    obj = storage_service.upload(b"checksum-me", "c.bin", artifact_type=ArtifactType.temporary_upload)
    assert storage_service.verify_checksum(obj.object_id) is True


def test_duplicate_detection_rejects_when_disabled():
    storage_service.upload(b"dup", "one.bin", artifact_type=ArtifactType.temporary_upload, allow_duplicate=True)
    with pytest.raises(storage_service.StorageError) as exc:
        storage_service.upload(b"dup", "two.bin", artifact_type=ArtifactType.temporary_upload, allow_duplicate=False)
    assert exc.value.status_code == 409


def test_archive_restore_delete_lifecycle():
    obj = storage_service.upload(b"x", "x.bin", artifact_type=ArtifactType.workflow_artifact)
    archived = storage_service.archive(obj.object_id)
    assert archived.status == StorageObjectStatus.archived
    restored = storage_service.restore(obj.object_id)
    assert restored.status == StorageObjectStatus.active
    deleted = storage_service.delete(obj.object_id)
    assert deleted.status == StorageObjectStatus.deleted


def test_copy_move_rename():
    obj = storage_service.upload(b"copy", "orig.txt", artifact_type=ArtifactType.knowledge_document)
    copied = storage_service.copy(obj.object_id, new_name="copy.txt")
    assert copied.object_id != obj.object_id
    renamed = storage_service.rename(obj.object_id, "renamed.txt")
    assert renamed.name == "renamed.txt"
    moved = storage_service.move(obj.object_id, workspace_id="ws_1")
    assert moved.storage_metadata.workspace_id == "ws_1"


def test_storage_statistics():
    storage_service.upload(b"a", "a.bin", artifact_type=ArtifactType.dataset)
    storage_service.upload(b"bb", "b.bin", artifact_type=ArtifactType.report)
    stats = storage_service.storage_statistics()
    assert stats.total_objects == 2
    assert stats.total_bytes >= 3
    assert stats.by_artifact_type.get("dataset") == 1
