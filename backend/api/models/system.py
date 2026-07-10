from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str = "ok"
    app: str = ""
    version: str = ""
    api_gateway: str = "v1"
    services: dict[str, str] = Field(default_factory=dict)


class VersionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    app: str = ""
    version: str = ""
    api_gateway: str = "v1"
    schema_versions: dict[str, str] = Field(default_factory=dict)


class CapabilitiesResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    capabilities: list[str] = Field(default_factory=list)
    workflow_runners: list[str] = Field(default_factory=list)
    llm_providers: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
