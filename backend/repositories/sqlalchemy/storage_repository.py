from __future__ import annotations

"""SQLAlchemy-backed StorageMetadataStore (KI-009 / TD-011)."""

from backend.database.mappers.storage import orm_to_storage_object, storage_object_to_orm
from backend.database.models.storage import StorageObjectORM
from backend.models.storage_models import StorageObject
from backend.repositories.sqlalchemy.base import SQLAlchemyRepositoryBase
from backend.storage.interfaces import StorageMetadataStore


class SQLAlchemyStorageMetadataStore(SQLAlchemyRepositoryBase, StorageMetadataStore):
    """Durable StorageObject catalog via the project database layer."""

    def save(self, obj: StorageObject) -> StorageObject:
        with self._unit(write=True) as s:
            existing = s.get(StorageObjectORM, obj.object_id)
            s.merge(storage_object_to_orm(obj, existing))
        return obj.model_copy(deep=True)

    def get(self, object_id: str) -> StorageObject | None:
        with self._unit() as s:
            orm = s.get(StorageObjectORM, object_id)
            return orm_to_storage_object(orm) if orm else None

    def list(
        self,
        *,
        artifact_type: str | None = None,
        owner_id: str | None = None,
        organization_id: str | None = None,
        workspace_id: str | None = None,
        status: str | None = None,
    ) -> list[StorageObject]:
        with self._unit() as s:
            query = s.query(StorageObjectORM)
            if artifact_type:
                query = query.filter(StorageObjectORM.artifact_type == artifact_type)
            if owner_id:
                query = query.filter(StorageObjectORM.owner_id == owner_id)
            if organization_id:
                query = query.filter(StorageObjectORM.organization_id == organization_id)
            if workspace_id:
                query = query.filter(StorageObjectORM.workspace_id == workspace_id)
            if status:
                query = query.filter(StorageObjectORM.status == status)
            rows = query.all()
            items = [orm_to_storage_object(r) for r in rows]
        return sorted(items, key=lambda x: x.created_at, reverse=True)

    def find_by_checksum(self, checksum_value: str) -> StorageObject | None:
        if not checksum_value:
            return None
        with self._unit() as s:
            # Prefer indexed current checksum, then scan payloads for historical matches.
            orm = (
                s.query(StorageObjectORM)
                .filter(StorageObjectORM.current_checksum == checksum_value)
                .first()
            )
            if orm is not None:
                return orm_to_storage_object(orm)
            for row in s.query(StorageObjectORM).all():
                obj = orm_to_storage_object(row)
                for version in obj.versions:
                    if version.checksum.value == checksum_value:
                        return obj
        return None

    def delete(self, object_id: str) -> bool:
        with self._unit(write=True) as s:
            orm = s.get(StorageObjectORM, object_id)
            if orm is None:
                return False
            s.delete(orm)
            return True

    def clear(self) -> None:
        with self._unit(write=True) as s:
            s.query(StorageObjectORM).delete()
