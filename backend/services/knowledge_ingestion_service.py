from __future__ import annotations

import re
import itertools
from typing import Any

from backend.models.ai_insight_models import utc_now_iso
from backend.models.rag_models import (
    ALLOWED_KNOWLEDGE_SOURCES,
    FORBIDDEN_KNOWLEDGE_KEYS,
    RAG_SCHEMA_VERSION,
    KnowledgeChunk,
    KnowledgeDocument,
    empty_rag_future_extensions,
)
from backend.services.embedding_service import create_embedding
from backend.services.vector_store_service import add_vectors, delete_vectors, get_vector_store

_DOCUMENTS: dict[str, KnowledgeDocument] = {}
_CHUNKS: dict[str, KnowledgeChunk] = {}
_DOC_CHUNK_IDS: dict[str, list[str]] = {}
_ID_SEQ = itertools.count(1)


def _contains_forbidden(text: str, metadata: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    lower = str(text or "").lower()
    for forbidden in ("password=", "api_key=", "secret=", "bearer ", "private_key"):
        if forbidden in lower:
            issues.append(f"Forbidden content pattern: {forbidden.strip()}")
    for key in (metadata or {}):
        key_l = str(key).lower()
        if key_l in FORBIDDEN_KNOWLEDGE_KEYS or any(f in key_l for f in FORBIDDEN_KNOWLEDGE_KEYS):
            issues.append(f"Forbidden metadata key: {key}")
    return issues


def validate_document(
    *,
    title: str,
    content: str,
    source: str = "text",
    metadata: dict[str, Any] | None = None,
) -> dict[str, object]:
    issues: list[str] = []
    if not str(title or "").strip():
        issues.append("Missing title")
    if not str(content or "").strip():
        issues.append("Missing content")
    if source not in ALLOWED_KNOWLEDGE_SOURCES:
        issues.append(f"Knowledge source not allowed: {source}")
    issues.extend(_contains_forbidden(content, metadata))
    issues.extend(_contains_forbidden(title, None))
    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }


def chunk_document(
    document: KnowledgeDocument,
    *,
    max_chars: int = 280,
    overlap: int = 40,
) -> list[KnowledgeChunk]:
    """Split document content into overlapping text chunks."""
    text = str(document.content or "").strip()
    if not text:
        return []

    # Prefer paragraph / sentence boundaries when possible.
    parts = [p.strip() for p in re.split(r"\n\s*\n|(?<=[.!?])\s+", text) if p.strip()]
    if not parts:
        parts = [text]

    raw_chunks: list[str] = []
    buffer = ""
    for part in parts:
        candidate = f"{buffer} {part}".strip() if buffer else part
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        if buffer:
            raw_chunks.append(buffer)
        if len(part) <= max_chars:
            buffer = part
        else:
            start = 0
            while start < len(part):
                end = min(len(part), start + max_chars)
                raw_chunks.append(part[start:end].strip())
                if end >= len(part):
                    break
                start = max(0, end - overlap)
            buffer = ""
    if buffer:
        raw_chunks.append(buffer)

    # Apply overlap between consecutive assembled chunks when needed.
    chunks: list[KnowledgeChunk] = []
    for index, content in enumerate(raw_chunks):
        if not content:
            continue
        chunk_id = f"{document.document_id}_chunk_{index}"
        chunks.append(
            KnowledgeChunk(
                chunk_id=chunk_id,
                document_id=document.document_id,
                content=content,
                chunk_index=index,
                embedding_reference=f"emb::{chunk_id}",
                metadata={
                    "title": document.title,
                    "source": document.source,
                    "tags": list(document.tags),
                    **{k: v for k, v in document.metadata.items() if k not in FORBIDDEN_KNOWLEDGE_KEYS},
                },
            )
        )
    return chunks


def ingest_document(
    *,
    title: str,
    content: str = "",
    source: str = "text",
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    document_id: str | None = None,
    index: bool = True,
    max_chars: int = 280,
    storage_object_id: str | None = None,
) -> tuple[KnowledgeDocument, list[KnowledgeChunk]]:
    """Validate, store, chunk, and optionally index a knowledge document."""
    if storage_object_id:
        from backend.services import storage_service

        blob, storage_obj = storage_service.download(storage_object_id)
        content = blob.decode("utf-8", errors="replace")
        meta = dict(metadata or {})
        meta.setdefault("storage_object_id", storage_object_id)
        meta.setdefault("storage_name", storage_obj.name)
        metadata = meta
        if not title.strip():
            title = storage_obj.name
    validation = validate_document(title=title, content=content, source=source, metadata=metadata)
    if not validation["valid"]:
        raise ValueError(f"Invalid knowledge document: {validation['issues']}")

    now = utc_now_iso()
    stamp = now.replace(":", "").replace("-", "")
    doc = KnowledgeDocument(
        document_id=document_id or f"kdoc_{stamp}_{next(_ID_SEQ)}",
        title=title.strip(),
        content=content.strip(),
        source=source,
        metadata={
            **dict(metadata or {}),
            "schema": RAG_SCHEMA_VERSION,
            "future_extensions": empty_rag_future_extensions(),
        },
        created_at=now,
        tags=list(tags or []),
    )

    # Replace existing document if same id.
    if doc.document_id in _DOCUMENTS:
        remove_document(doc.document_id)

    chunks = chunk_document(doc, max_chars=max_chars)
    _DOCUMENTS[doc.document_id] = doc.model_copy(deep=True)
    _DOC_CHUNK_IDS[doc.document_id] = [c.chunk_id for c in chunks]
    for chunk in chunks:
        _CHUNKS[chunk.chunk_id] = chunk.model_copy(deep=True)

    if index and chunks:
        vectors = [create_embedding(c.content) for c in chunks]
        payloads = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "source": doc.source,
                "title": doc.title,
                "tags": list(doc.tags),
                "content": c.content,
            }
            for c in chunks
        ]
        add_vectors(
            [c.chunk_id for c in chunks],
            vectors,
            payloads=payloads,
        )

    try:
        from backend.monitoring.metrics import record_knowledge, record_rag

        record_knowledge(operation="ingest")
        if index and chunks:
            record_rag(operation="index")
    except Exception:
        pass

    return doc.model_copy(deep=True), [c.model_copy(deep=True) for c in chunks]


def list_documents() -> list[KnowledgeDocument]:
    return [d.model_copy(deep=True) for d in sorted(_DOCUMENTS.values(), key=lambda d: d.created_at)]


def get_document(document_id: str) -> KnowledgeDocument | None:
    item = _DOCUMENTS.get(document_id)
    return item.model_copy(deep=True) if item is not None else None


def get_chunk(chunk_id: str) -> KnowledgeChunk | None:
    item = _CHUNKS.get(chunk_id)
    return item.model_copy(deep=True) if item is not None else None


def list_chunks(document_id: str | None = None) -> list[KnowledgeChunk]:
    if document_id is None:
        return [c.model_copy(deep=True) for c in _CHUNKS.values()]
    ids = _DOC_CHUNK_IDS.get(document_id, [])
    return [_CHUNKS[i].model_copy(deep=True) for i in ids if i in _CHUNKS]


def remove_document(document_id: str) -> bool:
    if document_id not in _DOCUMENTS:
        return False
    chunk_ids = list(_DOC_CHUNK_IDS.get(document_id, []))
    if chunk_ids:
        delete_vectors(chunk_ids)
    for chunk_id in chunk_ids:
        _CHUNKS.pop(chunk_id, None)
    _DOC_CHUNK_IDS.pop(document_id, None)
    _DOCUMENTS.pop(document_id, None)
    return True


def clear_knowledge_store() -> None:
    _DOCUMENTS.clear()
    _CHUNKS.clear()
    _DOC_CHUNK_IDS.clear()
    get_vector_store().clear()


def knowledge_summary() -> dict[str, Any]:
    by_source: dict[str, int] = {}
    for doc in _DOCUMENTS.values():
        by_source[doc.source] = by_source.get(doc.source, 0) + 1
    return {
        "document_count": len(_DOCUMENTS),
        "chunk_count": len(_CHUNKS),
        "vector_count": get_vector_store().count(),
        "by_source": by_source,
        "schema": RAG_SCHEMA_VERSION,
    }
