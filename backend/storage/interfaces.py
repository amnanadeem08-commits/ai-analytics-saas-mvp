from __future__ import annotations

"""Storage provider + metadata-store interfaces (Sprint 8.4)."""

from abc import ABC, abstractmethod

from backend.models.storage_models import StorageObject


class StorageBackend(ABC):
    """Byte-level storage provider (local FS, S3, ...)."""

    provider_name: str = "abstract"

    @abstractmethod
    def write(self, key: str, content: bytes) -> None: ...

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> bool: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]: ...


class StorageMetadataStore(ABC):
    """Persistence for StorageObject records (metadata + version history)."""

    @abstractmethod
    def save(self, obj: StorageObject) -> StorageObject: ...

    @abstractmethod
    def get(self, object_id: str) -> StorageObject | None: ...

    @abstractmethod
    def list(
        self,
        *,
        artifact_type: str | None = None,
        owner_id: str | None = None,
        organization_id: str | None = None,
        workspace_id: str | None = None,
        status: str | None = None,
    ) -> list[StorageObject]: ...

    @abstractmethod
    def find_by_checksum(self, checksum_value: str) -> StorageObject | None: ...

    @abstractmethod
    def delete(self, object_id: str) -> bool: ...

    @abstractmethod
    def clear(self) -> None: ...
