from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.embedding_service import reset_embedding_provider
from backend.services.knowledge_ingestion_service import clear_knowledge_store
from backend.services.vector_store_service import reset_vector_store


def setup_function():
    reset_embedding_provider()
    reset_vector_store()
    clear_knowledge_store()


client = TestClient(app)


def test_knowledge_ingest_search_list_delete():
    ingested = client.post(
        "/api/v1/knowledge/ingest",
        json={
            "title": "API Knowledge Doc",
            "content": "North region revenue decline guidance for analysts.",
            "source": "manual",
            "tags": ["revenue", "north"],
        },
    )
    assert ingested.status_code == 201
    body = ingested.json()
    assert body["success"] is True
    document_id = body["document_id"]
    assert body["chunk_count"] >= 1

    listed = client.get("/api/v1/knowledge/documents")
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1

    search = client.post(
        "/api/v1/knowledge/search",
        json={"query": "revenue decline north", "top_k": 3},
    )
    assert search.status_code == 200
    assert search.json()["success"] is True
    assert search.json()["chunk_count"] >= 1

    deleted = client.delete(f"/api/v1/knowledge/{document_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    missing = client.delete("/api/v1/knowledge/missing_doc")
    assert missing.status_code == 404
    assert missing.json()["success"] is False


def test_knowledge_ingest_validation_error():
    response = client.post(
        "/api/v1/knowledge/ingest",
        json={"title": "", "content": ""},
    )
    assert response.status_code == 422
    assert response.json()["success"] is False
