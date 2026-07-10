from __future__ import annotations

"""Version management for storage objects (Sprint 8.4)."""

import uuid
from datetime import datetime, timezone

from backend.models.storage_models import FileChecksum, StorageObject, StorageVersion


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _version_id() -> str:
    return f"ver_{uuid.uuid4().hex[:12]}"


def _object_id() -> str:
    return f"obj_{uuid.uuid4().hex[:12]}"


def build_storage_key(
    *,
    artifact_type: str,
    object_id: str,
    version_number: int,
    filename: str,
) -> str:
    safe_name = filename.replace("\\", "/").split("/")[-1] or "blob"
    return f"{artifact_type}/{object_id}/v{version_number}/{safe_name}"


def create_object_with_version(
    *,
    name: str,
    artifact_type: str,
    provider: str,
    content: bytes,
    checksum: FileChecksum,
    content_type: str,
    owner_id: str = "",
    organization_id: str = "",
    workspace_id: str = "",
    created_by: str = "",
    metadata: dict | None = None,
    object_id: str | None = None,
) -> tuple[StorageObject, StorageVersion]:
    """Create a new storage object with its first version."""
    oid = object_id or _object_id()
    now = _now_iso()
    version = StorageVersion(
        version_id=_version_id(),
        version_number=1,
        storage_key=build_storage_key(
            artifact_type=artifact_type,
            object_id=oid,
            version_number=1,
            filename=name,
        ),
        checksum=checksum,
        size_bytes=len(content),
        content_type=content_type,
        created_at=now,
        created_by=created_by,
        is_current=True,
        metadata=dict(metadata or {}),
    )
    from backend.models.storage_models import ArtifactType, StorageMetadata, StorageProvider

    obj = StorageObject(
        object_id=oid,
        name=name,
        artifact_type=ArtifactType(artifact_type) if artifact_type in ArtifactType._value2member_map_ else ArtifactType.dataset,
        provider=StorageProvider(provider) if provider in StorageProvider._value2member_map_ else StorageProvider.local,
        current_version=1,
        versions=[version],
        storage_metadata=StorageMetadata(
            owner_id=owner_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            content_type=content_type,
            custom=dict(metadata or {}),
        ),
        created_at=now,
        updated_at=now,
        metadata=dict(metadata or {}),
    )
    return obj, version


def append_version(
    obj: StorageObject,
    *,
    name: str,
    content: bytes,
    checksum: FileChecksum,
    content_type: str,
    created_by: str = "",
    metadata: dict | None = None,
) -> StorageVersion:
    """Append a new version — never overwrites existing version records."""
    next_num = max((v.version_number for v in obj.versions), default=0) + 1
    now = _now_iso()
    for version in obj.versions:
        version.is_current = False
    version = StorageVersion(
        version_id=_version_id(),
        version_number=next_num,
        storage_key=build_storage_key(
            artifact_type=obj.artifact_type.value,
            object_id=obj.object_id,
            version_number=next_num,
            filename=name,
        ),
        checksum=checksum,
        size_bytes=len(content),
        content_type=content_type,
        created_at=now,
        created_by=created_by,
        is_current=True,
        metadata=dict(metadata or {}),
    )
    obj.versions.append(version)
    obj.current_version = next_num
    obj.name = name
    obj.updated_at = now
    obj.storage_metadata.content_type = content_type
    return version


def rollback(obj: StorageObject, version_number: int) -> StorageVersion:
    """Set a previous version as current without deleting newer versions."""
    target = next((v for v in obj.versions if v.version_number == version_number), None)
    if target is None:
        raise ValueError(f"Version {version_number} not found for object {obj.object_id}")
    for version in obj.versions:
        version.is_current = version.version_number == version_number
    obj.current_version = version_number
    obj.updated_at = _now_iso()
    return target


def get_version(obj: StorageObject, version_number: int | None = None) -> StorageVersion | None:
    if version_number is None:
        return obj.current()
    return next((v for v in obj.versions if v.version_number == version_number), None)


def trim_versions(obj: StorageObject, max_versions: int) -> list[StorageVersion]:
    """Return versions that exceed retention max_versions (oldest non-current first)."""
    if max_versions <= 0 or len(obj.versions) <= max_versions:
        return []
    sorted_versions = sorted(obj.versions, key=lambda v: v.version_number)
    keep = {v.version_id for v in sorted_versions[-max_versions:]}
    return [v for v in sorted_versions if v.version_id not in keep and not v.is_current]
