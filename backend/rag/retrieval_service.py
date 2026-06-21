from __future__ import annotations

from backend.rag.indexing_service import get_index_status
from backend.rag.vector_store import ChromaVectorStore


def retrieve_chunks(dataset_id: str, query: str, k: int = 5, chunk_types: list[str] | None = None) -> dict:
    status = get_index_status(dataset_id)
    if not status.get("indexed"):
        return {"dataset_id": dataset_id, "query": query, "k": k, "results": []}
    results = ChromaVectorStore().query_dataset(dataset_id=dataset_id, query=query, k=k, chunk_types=chunk_types)
    return {"dataset_id": dataset_id, "query": query, "k": k, "results": results}
