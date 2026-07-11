from __future__ import annotations

"""Mappers between StorageObject domain model and StorageObjectORM."""

from backend.database.models.storage import StorageObjectORM
from backend.models.storage_models import StorageObject


def _current_checksum(obj: StorageObject) -> str:
    current = obj.current()
    if current is None:
        return ""
    return current.checksum.value or ""


def storage_object_to_orm(obj: StorageObject, orm: StorageObjectORM | None = None) -> StorageObjectORM:
    target = orm or StorageObjectORM(object_id=obj.object_id)
    target.object_id = obj.object_id
    target.name = obj.name
    target.artifact_type = (
        obj.artifact_type.value if hasattr(obj.artifact_type, "value") else str(obj.artifact_type)
    )
    target.provider = obj.provider.value if hasattr(obj.provider, "value") else str(obj.provider)
    target.status = obj.status.value if hasattr(obj.status, "value") else str(obj.status)
    target.owner_id = obj.storage_metadata.owner_id or ""
    target.organization_id = obj.storage_metadata.organization_id or ""
    target.workspace_id = obj.storage_metadata.workspace_id or ""
    target.current_checksum = _current_checksum(obj)
    target.created_at = obj.created_at or ""
    target.updated_at = obj.updated_at or ""
    target.data = obj.model_dump(mode="json")
    return target


def orm_to_storage_object(orm: StorageObjectORM) -> StorageObject:
    return StorageObject.model_validate(orm.data or {})
