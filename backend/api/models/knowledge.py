from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = Field(..., min_length=1)
    content: str = ""
    source: str = "text"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    document_id: str | None = None
    index: bool = True
    storage_object_id: str | None = None


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    document_id: str
    title: str = ""
    source: str = ""
    chunk_count: int = 0
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    agent_name: str = ""
    filters: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    query: str = ""
    chunk_count: int = 0
    sources: list[str] = Field(default_factory=list)
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    relevance_scores: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
