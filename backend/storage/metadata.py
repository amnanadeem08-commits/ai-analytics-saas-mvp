from __future__ import annotations

"""In-memory metadata store for StorageObject records (Sprint 8.4)."""

import threading
from copy import deepcopy

from backend.models.storage_models import StorageObject
from backend.storage.interfaces import StorageMetadataStore


class InMemoryStorageMetadataStore(StorageMetadataStore):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._objects: dict[str, StorageObject] = {}

    def save(self, obj: StorageObject) -> StorageObject:
        with self._lock:
            stored = obj.model_copy(deep=True)
            self._objects[stored.object_id] = stored
            return stored.model_copy(deep=True)

    def get(self, object_id: str) -> StorageObject | None:
        with self._lock:
            obj = self._objects.get(object_id)
            return obj.model_copy(deep=True) if obj else None

    def list(
        self,
        *,
        artifact_type: str | None = None,
        owner_id: str | None = None,
        organization_id: str | None = None,
        workspace_id: str | None = None,
        status: str | None = None,
    ) -> list[StorageObject]:
        with self._lock:
            items = list(self._objects.values())
        if artifact_type:
            items = [o for o in items if o.artifact_type.value == artifact_type or str(o.artifact_type) == artifact_type]
        if owner_id:
            items = [o for o in items if o.storage_metadata.owner_id == owner_id]
        if organization_id:
            items = [o for o in items if o.storage_metadata.organization_id == organization_id]
        if workspace_id:
            items = [o for o in items if o.storage_metadata.workspace_id == workspace_id]
        if status:
            items = [o for o in items if o.status.value == status or str(o.status) == status]
        return [o.model_copy(deep=True) for o in sorted(items, key=lambda x: x.created_at, reverse=True)]

    def find_by_checksum(self, checksum_value: str) -> StorageObject | None:
        if not checksum_value:
            return None
        with self._lock:
            for obj in self._objects.values():
                current = obj.current()
                if current and current.checksum.value == checksum_value:
                    return obj.model_copy(deep=True)
                for version in obj.versions:
                    if version.checksum.value == checksum_value:
                        return obj.model_copy(deep=True)
        return None

    def delete(self, object_id: str) -> bool:
        with self._lock:
            return self._objects.pop(object_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._objects.clear()
