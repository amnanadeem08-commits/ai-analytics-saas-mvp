from __future__ import annotations

from backend.services import job_service
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
from backend.models.job_models import JobStatus


def setup_function():
    reset_llm_provider()
    reset_embedding_provider()
    reset_vector_store()
    clear_knowledge_store()
    reset_memory_store()
    clear_plans()
    clear_analyst_sessions()
    clear_evaluations()
    ensure_builtin_prompts(reset=True)
    ensure_builtin_tools(reset=True)
    ensure_builtin_agents(reset=True)
    job_service.reset_jobs()
    ingest_document(
        title="Revenue Playbook",
        content="When analyzing revenue decline, inspect regional KPIs; North often drives it.",
        source="analysis_guideline",
        tags=["revenue"],
    )


def test_execute_analysis_async_reuses_runtime():
    job = job_service.execute_analysis_async(query="Analyze revenue decline", inline=True)
    assert job.status == JobStatus.succeeded
    data = job.result.data
    assert data["answer"]
    assert data.get("session_id")


def test_execute_workflow_async_reuses_engine():
    job = job_service.execute_workflow_async(query="Analyze revenue decline", inline=True)
    assert job.status == JobStatus.succeeded
    assert job.result.data.get("execution_id")
    assert job.result.data.get("status") in {"completed", "partial", "failed"}


def test_evaluate_async_reuses_evaluation():
    analysis = job_service.execute_analysis_async(query="Analyze revenue decline", inline=True)
    session_id = analysis.result.data["session_id"]
    job = job_service.evaluate_async(session_id=session_id, inline=True)
    assert job.status == JobStatus.succeeded
    assert job.result.data.get("grade") in {"A", "B", "C", "D", "F"}


def test_knowledge_ingestion_async_reuses_service():
    job = job_service.knowledge_ingestion_async(
        title="Async Doc", content="North region revenue decline guidance.", inline=True
    )
    assert job.status == JobStatus.succeeded
    assert job.result.data.get("document_id")
    assert job.result.data.get("chunk_count", 0) >= 1
