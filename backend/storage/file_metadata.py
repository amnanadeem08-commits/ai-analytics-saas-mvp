from __future__ import annotations

"""File-backed durable StorageMetadataStore (KI-009).

Used when a SQL database is not configured. Survives process restarts via a
JSON index under the object-storage root directory.
"""

import json
import logging
import threading
from pathlib import Path

from backend.models.storage_models import StorageObject
from backend.storage.interfaces import StorageMetadataStore

_log = logging.getLogger("ai_analytics.storage.file_metadata")


class FileStorageMetadataStore(StorageMetadataStore):
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()
        self._objects: dict[str, StorageObject] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("Could not load storage metadata index %s: %s", self._path, exc)
            return
        if not isinstance(raw, dict):
            return
        items = raw.get("objects", raw) if isinstance(raw.get("objects", raw), dict) else {}
        if not isinstance(items, dict):
            return
        loaded: dict[str, StorageObject] = {}
        for object_id, payload in items.items():
            try:
                loaded[str(object_id)] = StorageObject.model_validate(payload)
            except Exception as exc:  # noqa: BLE001
                _log.warning("Skipping corrupt storage metadata for %s: %s", object_id, exc)
        self._objects = loaded

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1.0.0",
            "objects": {
                object_id: obj.model_dump(mode="json") for object_id, obj in self._objects.items()
            },
        }
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def save(self, obj: StorageObject) -> StorageObject:
        with self._lock:
            stored = obj.model_copy(deep=True)
            self._objects[stored.object_id] = stored
            self._persist()
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
            items = [
                o
                for o in items
                if o.artifact_type.value == artifact_type or str(o.artifact_type) == artifact_type
            ]
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
            removed = self._objects.pop(object_id, None) is not None
            if removed:
                self._persist()
            return removed

    def clear(self) -> None:
        with self._lock:
            self._objects.clear()
            self._persist()
