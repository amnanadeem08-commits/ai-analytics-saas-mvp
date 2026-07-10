from __future__ import annotations

import pytest

from backend.services.embedding_service import reset_embedding_provider
from backend.services.knowledge_ingestion_service import (
    chunk_document,
    clear_knowledge_store,
    ingest_document,
    knowledge_summary,
    list_chunks,
    list_documents,
    remove_document,
    validate_document,
)
from backend.services.vector_store_service import reset_vector_store


def setup_function():
    reset_embedding_provider()
    reset_vector_store()
    clear_knowledge_store()


def test_validate_and_ingest_document():
    assert validate_document(
        title="Revenue KPI",
        content="Revenue measures total sales amount.",
        source="kpi_definition",
    )["valid"] is True

    doc, chunks = ingest_document(
        title="Revenue KPI",
        content="Revenue measures total sales amount. Use it for growth tracking.",
        source="kpi_definition",
        tags=["kpi", "revenue"],
    )
    assert doc.document_id
    assert chunks
    assert list_documents()
    assert list_chunks(doc.document_id)
    summary = knowledge_summary()
    assert summary["document_count"] == 1
    assert summary["chunk_count"] >= 1
    assert summary["vector_count"] >= 1


def test_chunking_splits_long_content():
    long = "Sentence one about revenue. " * 40
    doc, chunks = ingest_document(
        title="Long Guide",
        content=long,
        source="analysis_guideline",
        max_chars=120,
    )
    assert len(chunks) >= 2
    rebuilt = chunk_document(doc, max_chars=120)
    assert len(rebuilt) >= 2


def test_remove_document_and_forbidden_content():
    doc, _ = ingest_document(
        title="Temp",
        content="Temporary business rule for margins.",
        source="business_rule",
    )
    assert remove_document(doc.document_id) is True
    assert list_documents() == []

    with pytest.raises(ValueError):
        ingest_document(
            title="Bad",
            content="password=supersecret",
            source="text",
        )
    with pytest.raises(ValueError):
        ingest_document(
            title="Bad Source",
            content="ok",
            source="not_allowed",
        )
