from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.agent_service import ensure_builtin_agents
from backend.services.ai_analyst_runtime_service import clear_analyst_sessions
from backend.services.embedding_service import reset_embedding_provider
from backend.services.evaluation_service import clear_evaluations
from backend.services.knowledge_ingestion_service import clear_knowledge_store, ingest_document
from backend.services.llm_service import reset_llm_provider
from backend.services.memory_service import reset_memory_store
from backend.services.planning_service import clear_plans
from backend.services.prompt_service import ensure_builtin_prompts
from backend.services.tool_registry_service import ensure_builtin_tools
from backend.services.vector_store_service import reset_vector_store
from backend.services.workflow_engine_service import clear_execution_store


def setup_function():
    reset_llm_provider()
    reset_embedding_provider()
    reset_vector_store()
    clear_knowledge_store()
    reset_memory_store()
    clear_plans()
    clear_analyst_sessions()
    clear_evaluations()
    clear_execution_store()
    ensure_builtin_prompts(reset=True)
    ensure_builtin_tools(reset=True)
    ensure_builtin_agents(reset=True)
    ingest_document(
        title="Region Drivers",
        content="North region often drives revenue decline; inspect regional KPIs first.",
        source="analysis_guideline",
        tags=["revenue", "region"],
    )


client = TestClient(app)


def test_workflow_execute_analyst_shortcut():
    response = client.post(
        "/api/v1/workflow/execute",
        json={"query": "Analyze revenue decline", "include_evaluation": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["execution_id"]
    assert body["status"] in {"completed", "partial", "failed"}

    status = client.get(f"/api/v1/workflow/status/{body['execution_id']}")
    assert status.status_code == 200
    assert status.json()["execution_id"] == body["execution_id"]

    results = client.get(f"/api/v1/workflow/results/{body['execution_id']}")
    assert results.status_code == 200
    assert "stage_results" in results.json()

    stats = client.get("/api/v1/workflow/statistics", params={"execution_id": body["execution_id"]})
    assert stats.status_code == 200
    assert stats.json()["execution_count"] == 1

    aggregate = client.get("/api/v1/workflow/statistics")
    assert aggregate.status_code == 200
    assert aggregate.json()["execution_count"] >= 1


def test_workflow_missing_execution():
    response = client.get("/api/v1/workflow/status/missing_exec")
    assert response.status_code == 404
    assert response.json()["success"] is False
