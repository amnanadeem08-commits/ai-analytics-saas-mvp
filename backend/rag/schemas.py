from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ChunkType = Literal[
    "dataset_summary",
    "schema_column",
    "profile_summary",
    "generated_insight",
    "row_sample",
]


class RagChunk(BaseModel):
    chunk_id: str
    dataset_id: str
    chunk_type: ChunkType
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagIndexRequest(BaseModel):
    rebuild: bool = False
    max_row_samples: int = Field(default=20, ge=0, le=100)


class RagIndexResponse(BaseModel):
    dataset_id: str
    status: str
    chunk_count: int
    collection: str
    embedding_model: str
    index_path: str
    message: str | None = None


class RagStatusResponse(BaseModel):
    dataset_id: str
    indexed: bool
    status: str
    chunk_count: int = 0
    collection: str = "analytics_chunks"
    embedding_model: str | None = None
    index_path: str | None = None
    last_indexed_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)
    k: int = Field(default=5, ge=1, le=20)
    chunk_types: list[ChunkType] | None = None


class RagRetrievedChunk(BaseModel):
    chunk_id: str
    dataset_id: str
    chunk_type: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float
    distance: float | None = None


class RagRetrieveResponse(BaseModel):
    dataset_id: str
    query: str
    k: int
    results: list[RagRetrievedChunk]


class RagDeleteResponse(BaseModel):
    dataset_id: str
    deleted: bool
    message: str
