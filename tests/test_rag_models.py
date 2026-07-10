from __future__ import annotations

from backend.models.rag_models import (
    ALLOWED_KNOWLEDGE_SOURCES,
    KnowledgeChunk,
    KnowledgeDocument,
    RetrievalQuery,
    RetrievalResult,
)


def test_rag_model_construction():
    doc = KnowledgeDocument(
        document_id="d1",
        title="KPI Guide",
        content="Revenue KPI measures total sales.",
        source="kpi_definition",
        tags=["kpi"],
    )
    chunk = KnowledgeChunk(
        chunk_id="d1_chunk_0",
        document_id="d1",
        content=doc.content,
        embedding_reference="emb::d1_chunk_0",
    )
    query = RetrievalQuery(query="revenue kpi", top_k=3)
    result = RetrievalResult(
        chunks=[chunk],
        relevance_scores=[0.9],
        sources=["kpi_definition"],
        query=query.query,
    )
    assert doc.source in ALLOWED_KNOWLEDGE_SOURCES
    assert result.chunks[0].document_id == "d1"
    assert result.relevance_scores[0] == 0.9
