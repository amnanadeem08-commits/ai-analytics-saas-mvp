from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

STORAGE_SCHEMA_VERSION = "1.0.0"

STORAGE_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "encryption",
    "cdn",
    "cloud_deployment",
    "lifecycle_automation",
    "billing",
)


def empty_storage_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in STORAGE_FUTURE_EXTENSION_KEYS}


class StorageProvider(str, Enum):
    local = "local"
    s3 = "s3"


class ArtifactType(str, Enum):
    dataset = "dataset"
    knowledge_document = "knowledge_document"
    report = "report"
    evaluation_export = "evaluation_export"
    workflow_artifact = "workflow_artifact"
    temporary_upload = "temporary_upload"
    ai_export = "ai_export"


class StorageObjectStatus(str, Enum):
    active = "active"
    archived = "archived"
    deleted = "deleted"


class DatasetStatus(str, Enum):
    active = "active"
    archived = "archived"
    deleted = "deleted"


class FileChecksum(BaseModel):
    model_config = ConfigDict(extra="allow")

    algorithm: str = "sha256"
    value: str = ""
    size_bytes: int = 0


class StorageVersion(BaseModel):
    model_config = ConfigDict(extra="allow")

    version_id: str
    version_number: int = 1
    storage_key: str = ""
    checksum: FileChecksum = Field(default_factory=FileChecksum)
    size_bytes: int = 0
    content_type: str = "application/octet-stream"
    created_at: str = ""
    created_by: str = ""
    is_current: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class StorageMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    owner_id: str = ""
    organization_id: str = ""
    workspace_id: str = ""
    tags: list[str] = Field(default_factory=list)
    content_type: str = "application/octet-stream"
    custom: dict[str, Any] = Field(default_factory=dict)


class RetentionPolicy(BaseModel):
    model_config = ConfigDict(extra="allow")

    policy_id: str = "default"
    max_versions: int = 10
    ttl_days: int | None = None  # None = keep indefinitely
    archive_after_days: int | None = None
    delete_archived_after_days: int | None = None


class StorageObject(BaseModel):
    """A logical stored artifact with one or more versions."""

    model_config = ConfigDict(extra="allow")

    object_id: str
    name: str
    artifact_type: ArtifactType = ArtifactType.dataset
    provider: StorageProvider = StorageProvider.local
    status: StorageObjectStatus = StorageObjectStatus.active
    current_version: int = 0
    versions: list[StorageVersion] = Field(default_factory=list)
    storage_metadata: StorageMetadata = Field(default_factory=StorageMetadata)
    retention_policy: RetentionPolicy = Field(default_factory=RetentionPolicy)
    created_at: str = ""
    updated_at: str = ""
    archived_at: str = ""
    schema_version: str = STORAGE_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)

    def current(self) -> StorageVersion | None:
        for version in self.versions:
            if version.version_number == self.current_version:
                return version
        return self.versions[-1] if self.versions else None


class StorageStatistics(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_objects: int = 0
    active_objects: int = 0
    archived_objects: int = 0
    deleted_objects: int = 0
    total_versions: int = 0
    total_bytes: int = 0
    by_artifact_type: dict[str, int] = Field(default_factory=dict)
    quota_bytes: int = 0
    quota_used_pct: float = 0.0
    provider: str = "local"
