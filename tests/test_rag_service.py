from __future__ import annotations

from backend.services.embedding_service import reset_embedding_provider
from backend.services.knowledge_ingestion_service import clear_knowledge_store, ingest_document
from backend.services.rag_service import (
    build_rag_context,
    rank_results,
    retrieve_knowledge,
    validate_retrieval,
)
from backend.services.vector_store_service import reset_vector_store


def setup_function():
    reset_embedding_provider()
    reset_vector_store()
    clear_knowledge_store()


def _seed_knowledge():
    ingest_document(
        title="Revenue KPI Definition",
        content="Revenue KPI measures total sales amount across regions including North.",
        source="kpi_definition",
        tags=["kpi", "revenue"],
    )
    ingest_document(
        title="Decline Analysis Guideline",
        content="When analyzing customer revenue decline, profile the dataset and inspect regional KPIs.",
        source="analysis_guideline",
        tags=["analysis", "decline"],
    )
    ingest_document(
        title="Unrelated Astronomy Note",
        content="Nebulas and telescopes are unrelated to business analytics.",
        source="documentation",
        tags=["astronomy"],
    )


def test_retrieve_and_rank_knowledge():
    _seed_knowledge()
    result = retrieve_knowledge("Analyze customer revenue decline", top_k=3)
    assert result.chunks
    assert validate_retrieval(result)["valid"] is True
    assert result.relevance_scores[0] >= result.relevance_scores[-1]
    top_text = " ".join(c.content.lower() for c in result.chunks[:2])
    assert "revenue" in top_text or "decline" in top_text


def test_build_rag_context_merges_runtime():
    _seed_knowledge()
    bundle = build_rag_context(
        "Find important revenue KPIs",
        agent_name="Data Analyst Agent",
        runtime_context={"dataset_id": "sales_q1"},
        top_k=3,
    )
    assert bundle.merged_context["dataset_id"] == "sales_q1"
    assert bundle.rag_snippets
    assert bundle.merged_context["rag_chunk_ids"]
    assert "rag_context_text" in bundle.merged_context

    ranked = rank_results(
        [{"id": "a", "score": 0.5, "payload": {"content": "revenue kpi", "title": "kpi"}}],
        query="revenue kpi",
    )
    assert ranked[0]["score"] >= 0.5
