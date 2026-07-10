from __future__ import annotations

from backend.models.storage_models import RetentionPolicy, StorageObject, StorageObjectStatus
from backend.storage.retention import evaluate_retention, validate_metadata
from backend.storage.versioning import append_version, create_object_with_version, rollback, trim_versions
from backend.storage.checksum import build_checksum


def test_validate_metadata():
    ok = validate_metadata(name="file.csv", artifact_type="dataset")
    assert ok["valid"] is True
    bad = validate_metadata(name="", artifact_type="dataset")
    assert bad["valid"] is False


def test_retention_evaluate_archive_and_trim():
    obj, _ = create_object_with_version(
        name="old.csv",
        artifact_type="dataset",
        provider="local",
        content=b"x",
        checksum=build_checksum(b"x"),
        content_type="text/csv",
    )
    obj.created_at = "2020-01-01T00:00:00Z"
    obj.retention_policy = RetentionPolicy(max_versions=2, archive_after_days=1)
    result = evaluate_retention(obj)
    assert "archive" in result["actions"]

    for i in range(3):
        append_version(
            obj,
            name=f"v{i}.csv",
            content=f"v{i}".encode(),
            checksum=build_checksum(f"v{i}".encode()),
            content_type="text/csv",
        )
    excess = trim_versions(obj, 2)
    assert len(excess) >= 1


def test_rollback_marks_current():
    obj, _ = create_object_with_version(
        name="a.txt",
        artifact_type="temporary_upload",
        provider="local",
        content=b"1",
        checksum=build_checksum(b"1"),
        content_type="text/plain",
    )
    append_version(
        obj,
        name="a.txt",
        content=b"2",
        checksum=build_checksum(b"2"),
        content_type="text/plain",
    )
    rollback(obj, 1)
    current = obj.current()
    assert current is not None
    assert current.version_number == 1
