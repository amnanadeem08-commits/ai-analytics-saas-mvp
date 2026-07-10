from __future__ import annotations

from backend.services import storage_service
from backend.services.knowledge_ingestion_service import clear_knowledge_store, ingest_document


def setup_function():
    storage_service.reset_storage()
    clear_knowledge_store()


def test_knowledge_ingestion_from_storage_object():
    obj = storage_service.upload(
        b"Our product roadmap includes AI analytics and forecasting.",
        "roadmap.txt",
        artifact_type="knowledge_document",
    )
    doc, chunks = ingest_document(
        title="Roadmap",
        content="",
        storage_object_id=obj.object_id,
    )
    assert doc.document_id
    assert len(chunks) >= 1
    assert doc.metadata.get("storage_object_id") == obj.object_id


def test_evaluation_export_creates_storage_artifact():
    from backend.services.evaluation_service import clear_evaluations, evaluate_session

    clear_evaluations()
    session = {
        "session_id": "sess_storage_test",
        "query": "Analyze revenue",
        "status": "completed",
        "result": {
            "answer": "Revenue declined due to churn.",
            "insights": ["Churn increased"],
            "recommendations": ["Improve retention"],
            "validation_status": "valid",
        },
    }
    run = evaluate_session(session)
    assert run.metadata.get("storage_object_id")
    obj = storage_service.get_metadata(run.metadata["storage_object_id"])
    assert obj is not None
    assert obj.artifact_type.value == "evaluation_export"
