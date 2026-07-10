from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

API_KEY_SCHEMA_VERSION = "1.0.0"

API_KEY_PREFIX = "databot_sk_"


class ApiKeyStatus(str, Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"


class ApiKeyScope(str, Enum):
    read = "read"
    write = "write"
    admin = "admin"
    ai_analyst = "ai_analyst"
    workflows = "workflows"
    knowledge = "knowledge"
    storage = "storage"
    jobs = "jobs"


class ApiKey(BaseModel):
    model_config = ConfigDict(extra="allow")

    key_id: str
    name: str
    key_prefix: str = ""
    key_hash: str = Field(default="", repr=False)
    organization_id: str
    workspace_id: str = ""
    created_by: str = ""
    scopes: list[str] = Field(default_factory=list)
    status: ApiKeyStatus = ApiKeyStatus.active
    rate_limit_per_minute: int = 60
    expires_at: str = ""
    last_used_at: str = ""
    created_at: str = ""
    revoked_at: str = ""
    rotated_from: str = ""
    schema_version: str = API_KEY_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)

    def public_dict(self) -> dict[str, Any]:
        data = self.model_dump(exclude={"key_hash"})
        data.pop("key_hash", None)
        return data
