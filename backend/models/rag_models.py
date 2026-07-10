from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

RAG_SCHEMA_VERSION = "1.0.0"

RAG_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "openai_embeddings",
    "huggingface_embeddings",
    "local_embeddings",
    "faiss",
    "chroma",
    "pinecone",
    "pgvector",
)


def empty_rag_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in RAG_FUTURE_EXTENSION_KEYS}


class KnowledgeSourceType(str, Enum):
    text = "text"
    business_rule = "business_rule"
    kpi_definition = "kpi_definition"
    analysis_guideline = "analysis_guideline"
    approved_insight = "approved_insight"
    documentation = "documentation"


ALLOWED_KNOWLEDGE_SOURCES: frozenset[str] = frozenset(
    {
        "text",
        "business_rule",
        "kpi_definition",
        "analysis_guideline",
        "approved_insight",
        "documentation",
        "manual",
    }
)

FORBIDDEN_KNOWLEDGE_KEYS: frozenset[str] = frozenset(
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
        "ssn",
        "credit_card",
    }
)


class KnowledgeDocument(BaseModel):
    """Approved knowledge document for RAG ingestion."""

    model_config = ConfigDict(extra="allow")

    document_id: str
    title: str
    content: str
    source: str = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    tags: list[str] = Field(default_factory=list)


class KnowledgeChunk(BaseModel):
    """One searchable chunk derived from a knowledge document."""

    model_config = ConfigDict(extra="allow")

    chunk_id: str
    document_id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding_reference: str = ""
    chunk_index: int = 0


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(extra="allow")

    query: str
    agent_name: str = ""
    top_k: int = 5
    filters: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    chunks: list[KnowledgeChunk] = Field(default_factory=list)
    relevance_scores: list[float] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    query: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagContextBundle(BaseModel):
    """Assembled RAG context ready for agent/workflow consumption."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    query: str = ""
    agent_name: str = ""
    retrieval: RetrievalResult = Field(default_factory=RetrievalResult)
    rag_snippets: list[dict[str, Any]] = Field(default_factory=list)
    merged_context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
