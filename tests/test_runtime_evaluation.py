from __future__ import annotations

from backend.models.workflow_models import WorkflowDefinition, WorkflowStatus
from backend.services.agent_service import ensure_builtin_agents
from backend.services.ai_analyst_runtime_service import (
    analyze_query,
    clear_analyst_sessions,
    get_session,
)
from backend.services.embedding_service import reset_embedding_provider
from backend.services.evaluation_service import clear_evaluations, get_evaluation
from backend.services.knowledge_ingestion_service import clear_knowledge_store, ingest_document
from backend.services.llm_service import reset_llm_provider
from backend.services.memory_service import reset_memory_store
from backend.services.planning_service import clear_plans
from backend.services.prompt_service import ensure_builtin_prompts
from backend.services.tool_registry_service import ensure_builtin_tools
from backend.services.vector_store_service import reset_vector_store
from backend.services.workflow_engine_service import (
    CTX_EVALUATION,
    CTX_EVALUATION_REPORT,
    DEFAULT_STAGE_RUNNERS,
    execute_workflow,
    make_analyst_stage,
    make_evaluation_stage,
)


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
    ingest_document(
        title="Revenue Decline Playbook",
        content=(
            "Guideline: when analyzing customer revenue decline, "
            "profile the dataset, inspect regional KPIs, and validate insights. "
            "North region is a common driver of decline."
        ),
        source="analysis_guideline",
        tags=["revenue", "decline", "region"],
    )


def test_evaluation_runner_registered():
    assert "evaluation_runner" in DEFAULT_STAGE_RUNNERS
    assert len(DEFAULT_STAGE_RUNNERS) == 24


def test_runtime_evaluation_after_analysis():
    response = analyze_query(
        "Analyze revenue decline",
        user_context={"dataset_id": "sales_q1"},
        initial_context={"dataset_id": "sales_q1"},
    )
    # Evaluation attached without altering answer content contract
    assert response.answer
    assert response.metadata.get("evaluation_id")
    assert response.metadata.get("evaluation_grade") in {"A", "B", "C", "D", "F"}
    assert isinstance(response.metadata.get("evaluation_score"), float)

    export = response.metadata.get("evaluation_export") or {}
    assert export.get("evaluation_id") == response.metadata["evaluation_id"]
    assert "metrics_summary" in export
    assert "score_breakdown" in export
    assert "report" in export
    assert export.get("read_only") is True

    run = get_evaluation(response.metadata["evaluation_id"])
    assert run is not None
    assert run.report is not None

    # Original analytical fields remain present (evaluation is additive metadata only)
    session = get_session(response.metadata["session_id"])
    assert session is not None
    assert session.result is not None
    assert session.result.answer == response.answer


def test_workflow_evaluation_stage_integration():
    definition = WorkflowDefinition(
        workflow_id="wf_eval_integration",
        workflow_name="Analyst + Evaluation",
        stages=[
            make_analyst_stage(
                stage_id="analyst",
                query="Analyze revenue decline",
                execution_order=1,
                user_context={"dataset_id": "sales_q1"},
            ),
            make_evaluation_stage(
                stage_id="evaluation",
                dependencies=["analyst"],
                execution_order=2,
            ),
        ],
        stop_on_error=False,
    )
    execution, ctx = execute_workflow(
        definition,
        initial_context={"dataset_id": "sales_q1", "user_query": "Analyze revenue decline"},
        stop_on_error=False,
    )
    assert execution.status in {WorkflowStatus.completed, WorkflowStatus.partial}
    assert CTX_EVALUATION in ctx
    assert CTX_EVALUATION_REPORT in ctx
    assert ctx.get("evaluation_id")
    assert ctx.get("evaluation_grade") in {"A", "B", "C", "D", "F"}
    export = ctx.get("evaluation_export") or {}
    assert "metrics_summary" in export
    # Analyst answer still present — evaluation did not replace it
    assert ctx.get("analyst_answer") or ctx.get("analyst_runtime_response")
