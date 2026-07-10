from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.models.rag_models import (
    KnowledgeChunk,
    RagContextBundle,
    RetrievalQuery,
    RetrievalResult,
)
from backend.services.embedding_service import create_embedding
from backend.services.knowledge_ingestion_service import get_chunk, get_document
from backend.services.vector_store_service import search_vectors


def validate_retrieval(result: RetrievalResult) -> dict[str, object]:
    issues: list[str] = []
    if result.query == "" and not result.chunks:
        issues.append("Empty retrieval result")
    if len(result.chunks) != len(result.relevance_scores):
        issues.append("chunks/relevance_scores length mismatch")
    for score in result.relevance_scores:
        if not isinstance(score, (int, float)):
            issues.append("Non-numeric relevance score")
            break
        if score < 0 or score > 1:
            issues.append(f"Relevance score out of range: {score}")
            break
    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "chunk_count": len(result.chunks),
    }


def rank_results(
    rows: list[dict[str, Any]],
    *,
    query: str = "",
) -> list[dict[str, Any]]:
    """Re-rank vector hits with a lexical boost for query-token overlap."""
    tokens = [t for t in str(query or "").lower().split() if len(t) > 2]
    ranked: list[dict[str, Any]] = []
    for row in rows:
        score = float(row.get("score") or 0.0)
        content = str((row.get("payload") or {}).get("content") or "").lower()
        title = str((row.get("payload") or {}).get("title") or "").lower()
        blob = f"{title} {content}"
        hits = sum(1 for token in tokens if token in blob)
        if tokens:
            coverage = hits / len(tokens)
            # Hybrid: keep semantic score but strongly prefer lexical coverage.
            score = (0.35 * score) + (0.65 * coverage)
            if hits:
                score += min(0.15, 0.03 * hits)
        ranked.append({**row, "score": round(min(1.0, score), 8)})
    ranked.sort(key=lambda r: (-r["score"], r["id"]))
    return ranked


def retrieve_knowledge(
    query: RetrievalQuery | str,
    *,
    agent_name: str = "",
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
) -> RetrievalResult:
    """Query → embedding → vector search → ranking → RetrievalResult."""
    if isinstance(query, str):
        rq = RetrievalQuery(
            query=query,
            agent_name=agent_name,
            top_k=top_k,
            filters=dict(filters or {}),
        )
    else:
        rq = query.model_copy(deep=True)
        if agent_name and not rq.agent_name:
            rq.agent_name = agent_name
        if filters:
            rq.filters = {**rq.filters, **filters}

    if not str(rq.query or "").strip():
        return RetrievalResult(query="", metadata={"empty_query": True})

    vector = create_embedding(rq.query)
    hits = search_vectors(vector, top_k=max(1, rq.top_k), filters=rq.filters or None)
    ranked = rank_results(hits, query=rq.query)

    chunks: list[KnowledgeChunk] = []
    scores: list[float] = []
    sources: list[str] = []
    for row in ranked:
        chunk = get_chunk(str(row["id"]))
        payload = row.get("payload") or {}
        if chunk is None:
            # Reconstruct from payload if chunk registry was cleared unexpectedly.
            chunk = KnowledgeChunk(
                chunk_id=str(row["id"]),
                document_id=str(payload.get("document_id") or ""),
                content=str(payload.get("content") or ""),
                embedding_reference=f"emb::{row['id']}",
                metadata=dict(payload),
            )
        chunks.append(chunk)
        scores.append(float(row["score"]))
        source = str(payload.get("source") or chunk.metadata.get("source") or "")
        if source and source not in sources:
            sources.append(source)
        doc = get_document(chunk.document_id)
        if doc is not None and doc.title and doc.title not in sources:
            sources.append(doc.title)

    return RetrievalResult(
        chunks=chunks,
        relevance_scores=scores,
        sources=sources,
        query=rq.query,
        metadata={
            "agent_name": rq.agent_name,
            "top_k": rq.top_k,
            "hit_count": len(chunks),
            "filters": dict(rq.filters),
        },
    )


def build_rag_context(
    query: str,
    *,
    agent_name: str = "",
    runtime_context: Mapping[str, Any] | None = None,
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
) -> RagContextBundle:
    """Assemble RAG snippets and merge into runtime context for planning/agents."""
    retrieval = retrieve_knowledge(
        query,
        agent_name=agent_name,
        top_k=top_k,
        filters=filters,
    )
    snippets: list[dict[str, Any]] = []
    for chunk, score in zip(retrieval.chunks, retrieval.relevance_scores, strict=False):
        snippets.append(
            {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "relevance": score,
                "source": chunk.metadata.get("source"),
                "title": chunk.metadata.get("title"),
                "tags": list(chunk.metadata.get("tags") or []),
            }
        )

    merged = dict(runtime_context or {})
    merged["rag_snippets"] = snippets
    merged["rag_chunk_ids"] = [s["chunk_id"] for s in snippets]
    merged["rag_sources"] = list(retrieval.sources)
    merged["rag_query"] = query
    if agent_name:
        merged["rag_agent_name"] = agent_name
    # Compact text block useful for planners / mock LLM prompts.
    if snippets:
        merged["rag_context_text"] = "\n".join(
            f"- ({s['relevance']:.3f}) {s['content']}" for s in snippets
        )

    return RagContextBundle(
        query=query,
        agent_name=agent_name,
        retrieval=retrieval,
        rag_snippets=snippets,
        merged_context=merged,
        metadata={
            "chunk_count": len(snippets),
            "validation": validate_retrieval(retrieval),
            "sources": list(retrieval.sources),
        },
    )
