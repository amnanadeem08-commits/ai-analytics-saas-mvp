from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

MEMORY_SCHEMA_VERSION = "1.0.0"

MEMORY_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "postgresql",
    "redis",
    "vector_store",
    "document_store",
    "embeddings",
)


def empty_memory_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in MEMORY_FUTURE_EXTENSION_KEYS}


class MemoryType(str, Enum):
    SHORT_TERM = "SHORT_TERM"
    TASK_MEMORY = "TASK_MEMORY"
    KNOWLEDGE_MEMORY = "KNOWLEDGE_MEMORY"
    EXECUTION_HISTORY = "EXECUTION_HISTORY"


# Content categories that are allowed to be persisted.
ALLOWED_MEMORY_SOURCES: frozenset[str] = frozenset(
    {
        "task_summary",
        "tool_result",
        "validation_result",
        "business_insight",
        "execution_history",
        "workflow_context",
        "manual",
    }
)

# Keys / patterns that must never be stored.
FORBIDDEN_CONTENT_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "credential",
        "authorization",
        "auth",
        "private_key",
        "access_key",
        "chain_of_thought",
        "hidden_reasoning",
        "cot",
    }
)


class AgentMemory(BaseModel):
    """One memory record. Functional store — not a metadata-only catalog."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    memory_id: str
    agent_name: str = ""
    memory_type: MemoryType = MemoryType.TASK_MEMORY
    content: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"
    relevance_score: float = 0.0
    created_at: str = ""
    expiry: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryQuery(BaseModel):
    model_config = ConfigDict(extra="allow")

    agent_name: str = ""
    query: str = ""
    memory_types: list[MemoryType] = Field(default_factory=list)
    limit: int = 10
    tags: list[str] = Field(default_factory=list)
    include_expired: bool = False


class MemoryResult(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    memories: list[AgentMemory] = Field(default_factory=list)
    relevance: list[float] = Field(default_factory=list)
    source_information: dict[str, Any] = Field(default_factory=dict)


class AgentContextBundle(BaseModel):
    """Merged runtime + memory context for planning/execution."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    agent_name: str = ""
    task: str = ""
    runtime_context: dict[str, Any] = Field(default_factory=dict)
    memory_result: MemoryResult = Field(default_factory=MemoryResult)
    memory_snippets: list[dict[str, Any]] = Field(default_factory=list)
    merged_context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
