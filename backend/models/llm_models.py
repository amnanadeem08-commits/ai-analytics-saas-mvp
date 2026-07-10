from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

LLM_SCHEMA_VERSION = "1.0.0"

LLM_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "streaming",
    "tool_calling",
    "multimodal",
    "cost_tracking",
    "rate_limiting",
)


def empty_llm_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in LLM_FUTURE_EXTENSION_KEYS}


class LLMProviderName(str, Enum):
    mock = "mock"
    openai = "openai"
    anthropic = "anthropic"
    local = "local"


class LLMProviderConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    provider_name: str = LLMProviderName.mock.value
    model_name: str = "mock-llm"
    temperature: float = 0.0
    max_tokens: int = 512
    enabled: bool = True
    api_key_env: str = ""
    base_url: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    prompt: str
    context: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    system: str = ""
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    content: str = ""
    structured_output: dict[str, Any] = Field(default_factory=dict)
    provider: str = ""
    model_name: str = ""
    usage_metadata: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)
    validation_status: str = "unchecked"
    metadata: dict[str, Any] = Field(default_factory=dict)
