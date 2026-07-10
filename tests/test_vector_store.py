from __future__ import annotations

from backend.services.embedding_service import create_embedding, reset_embedding_provider
from backend.services.vector_store_service import (
    FUTURE_VECTOR_BACKENDS,
    add_vectors,
    delete_vectors,
    get_vector_store,
    reset_vector_store,
    search_vectors,
)


def setup_function():
    reset_embedding_provider()
    reset_vector_store()


def test_add_search_delete_vectors():
    v1 = create_embedding("revenue decline analysis guideline")
    v2 = create_embedding("astronomy nebula telescope")
    add_vectors(
        ["c1", "c2"],
        [v1, v2],
        payloads=[
            {"chunk_id": "c1", "source": "analysis_guideline", "content": "revenue decline"},
            {"chunk_id": "c2", "source": "text", "content": "astronomy"},
        ],
    )
    assert get_vector_store().count() == 2
    hits = search_vectors(create_embedding("customer revenue decline"), top_k=2)
    assert hits
    assert hits[0]["id"] == "c1"
    assert hits[0]["score"] >= hits[-1]["score"]

    filtered = search_vectors(
        create_embedding("revenue"),
        top_k=5,
        filters={"source": "analysis_guideline"},
    )
    assert all(h["payload"]["source"] == "analysis_guideline" for h in filtered)
    assert delete_vectors(["c1"]) == 1
    assert get_vector_store().count() == 1
    assert "faiss" in FUTURE_VECTOR_BACKENDS
