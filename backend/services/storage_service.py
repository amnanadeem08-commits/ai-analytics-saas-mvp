from __future__ import annotations

"""Storage service (Sprint 8.4).

Central API for uploading, downloading, versioning, and managing stored artifacts.
Business logic in downstream services is unchanged — this layer handles bytes +
metadata only.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.models.storage_models import (
    ArtifactType,
    StorageObject,
    StorageObjectStatus,
    StorageStatistics,
)
from backend.storage.checksum import build_checksum, verify as verify_bytes
from backend.storage.config import get_storage_config
from backend.storage.factory import active_provider, get_backend, get_metadata_store, reset_storage_backends
from backend.storage.retention import evaluate_retention, validate_metadata
from backend.storage.versioning import (
    append_version,
    create_object_with_version,
    get_version,
    rollback,
    trim_versions,
)


class StorageError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def reset_storage() -> None:
    """Test helper — clear metadata store and rebuild backends."""
    reset_storage_backends()
    store = get_metadata_store()
    store.clear()
    config = get_storage_config()
    if not config.uses_s3:
        backend = get_backend()
        for key in backend.list_keys():
            backend.delete(key)


def upload(
    content: bytes,
    name: str,
    *,
    artifact_type: ArtifactType | str = ArtifactType.temporary_upload,
    owner_id: str = "",
    organization_id: str = "",
    workspace_id: str = "",
    content_type: str = "application/octet-stream",
    object_id: str | None = None,
    created_by: str = "",
    allow_duplicate: bool = True,
    metadata: dict[str, Any] | None = None,
) -> StorageObject:
    """Upload bytes — creates a new object or appends a version."""
    atype = artifact_type if isinstance(artifact_type, ArtifactType) else ArtifactType(str(artifact_type))
    validation = validate_metadata(
        name=name,
        artifact_type=atype.value,
        owner_id=owner_id,
        organization_id=organization_id,
        workspace_id=workspace_id,
    )
    if not validation["valid"]:
        raise StorageError(f"Invalid metadata: {validation['issues']}")

    checksum = build_checksum(content)
    meta_store = get_metadata_store()
    if not allow_duplicate:
        existing = meta_store.find_by_checksum(checksum.value)
        if existing is not None:
            raise StorageError(
                f"Duplicate content detected (checksum={checksum.value[:12]}…, object_id={existing.object_id})",
                status_code=409,
            )

    backend = get_backend()
    provider = active_provider()
    meta = dict(metadata or {})

    if object_id:
        obj = meta_store.get(object_id)
        if obj is None:
            raise StorageError(f"Storage object not found: {object_id}", status_code=404)
        if obj.status == StorageObjectStatus.deleted:
            raise StorageError(f"Storage object is deleted: {object_id}", status_code=410)
        version = append_version(
            obj,
            name=name,
            content=content,
            checksum=checksum,
            content_type=content_type,
            created_by=created_by,
            metadata=meta,
        )
        backend.write(version.storage_key, content)
        saved = meta_store.save(obj)
        _apply_version_retention(saved)
        try:
            from backend.monitoring.metrics import record_storage

            record_storage(operation="upload_version")
        except Exception:
            pass
        return saved

    obj, version = create_object_with_version(
        name=name,
        artifact_type=atype.value,
        provider=provider,
        content=content,
        checksum=checksum,
        content_type=content_type,
        owner_id=owner_id,
        organization_id=organization_id,
        workspace_id=workspace_id,
        created_by=created_by,
        metadata=meta,
    )
    backend.write(version.storage_key, content)
    saved = meta_store.save(obj)
    try:
        from backend.monitoring.metrics import record_storage

        record_storage(operation="upload")
    except Exception:
        pass
    return saved


def download(object_id: str, *, version_number: int | None = None) -> tuple[bytes, StorageObject]:
    obj = get_metadata(object_id)
    if obj is None:
        raise StorageError(f"Storage object not found: {object_id}", status_code=404)
    if obj.status == StorageObjectStatus.deleted:
        raise StorageError(f"Storage object is deleted: {object_id}", status_code=410)
    version = get_version(obj, version_number)
    if version is None:
        raise StorageError(f"Version not found for object {object_id}", status_code=404)
    content = get_backend().read(version.storage_key)
    return content, obj


def delete(object_id: str) -> StorageObject:
    obj = get_metadata(object_id)
    if obj is None:
        raise StorageError(f"Storage object not found: {object_id}", status_code=404)
    obj.status = StorageObjectStatus.deleted
    obj.updated_at = _now_iso()
    return get_metadata_store().save(obj)


def restore(object_id: str) -> StorageObject:
    obj = get_metadata(object_id)
    if obj is None:
        raise StorageError(f"Storage object not found: {object_id}", status_code=404)
    if obj.status not in {StorageObjectStatus.deleted, StorageObjectStatus.archived}:
        raise StorageError(f"Object is not restorable (status={obj.status.value})", status_code=409)
    obj.status = StorageObjectStatus.active
    obj.archived_at = ""
    obj.updated_at = _now_iso()
    return get_metadata_store().save(obj)


def archive(object_id: str) -> StorageObject:
    obj = get_metadata(object_id)
    if obj is None:
        raise StorageError(f"Storage object not found: {object_id}", status_code=404)
    if obj.status == StorageObjectStatus.deleted:
        raise StorageError("Cannot archive a deleted object", status_code=409)
    obj.status = StorageObjectStatus.archived
    obj.archived_at = _now_iso()
    obj.updated_at = _now_iso()
    return get_metadata_store().save(obj)


def copy(object_id: str, *, new_name: str | None = None, owner_id: str = "") -> StorageObject:
    content, obj = download(object_id)
    version = obj.current()
    if version is None:
        raise StorageError("Object has no current version", status_code=409)
    return upload(
        content,
        new_name or f"{obj.name}-copy",
        artifact_type=obj.artifact_type,
        owner_id=owner_id or obj.storage_metadata.owner_id,
        organization_id=obj.storage_metadata.organization_id,
        workspace_id=obj.storage_metadata.workspace_id,
        content_type=version.content_type,
        metadata=dict(obj.metadata),
        allow_duplicate=True,
    )


def move(
    object_id: str,
    *,
    workspace_id: str | None = None,
    organization_id: str | None = None,
) -> StorageObject:
    obj = get_metadata(object_id)
    if obj is None:
        raise StorageError(f"Storage object not found: {object_id}", status_code=404)
    if workspace_id is not None:
        obj.storage_metadata.workspace_id = workspace_id
    if organization_id is not None:
        obj.storage_metadata.organization_id = organization_id
    obj.updated_at = _now_iso()
    return get_metadata_store().save(obj)


def rename(object_id: str, new_name: str) -> StorageObject:
    if not str(new_name or "").strip():
        raise StorageError("new_name is required")
    obj = get_metadata(object_id)
    if obj is None:
        raise StorageError(f"Storage object not found: {object_id}", status_code=404)
    obj.name = new_name.strip()
    obj.updated_at = _now_iso()
    return get_metadata_store().save(obj)


def list_files(
    *,
    artifact_type: str | None = None,
    owner_id: str | None = None,
    organization_id: str | None = None,
    workspace_id: str | None = None,
    status: str | None = None,
) -> list[StorageObject]:
    return get_metadata_store().list(
        artifact_type=artifact_type,
        owner_id=owner_id,
        organization_id=organization_id,
        workspace_id=workspace_id,
        status=status,
    )


def get_metadata(object_id: str) -> StorageObject | None:
    return get_metadata_store().get(object_id)


def verify_checksum(object_id: str, *, version_number: int | None = None) -> bool:
    content, obj = download(object_id, version_number=version_number)
    version = get_version(obj, version_number)
    if version is None:
        return False
    return verify_bytes(content, version.checksum)


def rollback_version(object_id: str, version_number: int) -> StorageObject:
    obj = get_metadata(object_id)
    if obj is None:
        raise StorageError(f"Storage object not found: {object_id}", status_code=404)
    rollback(obj, version_number)
    return get_metadata_store().save(obj)


def storage_statistics() -> StorageStatistics:
    config = get_storage_config()
    objects = list_files()
    stats = StorageStatistics(provider=active_provider(), quota_bytes=config.quota_bytes)
    stats.total_objects = len(objects)
    total_bytes = 0
    total_versions = 0
    by_type: dict[str, int] = {}
    for obj in objects:
        total_versions += len(obj.versions)
        current = obj.current()
        if current:
            total_bytes += current.size_bytes
        by_type[obj.artifact_type.value] = by_type.get(obj.artifact_type.value, 0) + 1
        if obj.status == StorageObjectStatus.active:
            stats.active_objects += 1
        elif obj.status == StorageObjectStatus.archived:
            stats.archived_objects += 1
        elif obj.status == StorageObjectStatus.deleted:
            stats.deleted_objects += 1
    stats.total_bytes = total_bytes
    stats.total_versions = total_versions
    stats.by_artifact_type = by_type
    if config.quota_bytes > 0:
        stats.quota_used_pct = round(100.0 * total_bytes / config.quota_bytes, 2)
    return stats


def store_json_artifact(
    payload: dict[str, Any],
    *,
    name: str,
    artifact_type: ArtifactType | str,
    owner_id: str = "",
    organization_id: str = "",
    workspace_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> StorageObject:
    """Helper for evaluation/workflow exports."""
    content = json.dumps(payload, indent=2, default=str).encode("utf-8")
    return upload(
        content,
        name,
        artifact_type=artifact_type,
        owner_id=owner_id,
        organization_id=organization_id,
        workspace_id=workspace_id,
        content_type="application/json",
        metadata=metadata,
        allow_duplicate=True,
    )


def _apply_version_retention(obj: StorageObject) -> None:
    excess = trim_versions(obj, obj.retention_policy.max_versions or get_storage_config().default_max_versions)
    backend = get_backend()
    for version in excess:
        if backend.exists(version.storage_key):
            backend.delete(version.storage_key)
        obj.versions = [v for v in obj.versions if v.version_id != version.version_id]
    if excess:
        get_metadata_store().save(obj)


def new_object_id(prefix: str = "obj") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
