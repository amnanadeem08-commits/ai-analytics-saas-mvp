from __future__ import annotations

from backend.models.evaluation_models import EvaluationCategory, EvaluationStatus
from backend.models.workflow_models import StageRunResult, StageRunStatus, WorkflowExecution, WorkflowStatus
from backend.services.evaluation_service import (
    clear_evaluations,
    evaluate_agents,
    evaluate_llm,
    evaluate_rag,
    evaluate_session,
    evaluate_tools,
    evaluate_workflow,
    evaluate_workflow_run,
    evaluation_summary,
    export_evaluation,
    get_evaluation,
)


def setup_function():
    clear_evaluations()


def _sample_execution(*, status: WorkflowStatus = WorkflowStatus.completed) -> WorkflowExecution:
    return WorkflowExecution(
        execution_id="exec_eval_1",
        workflow_id="wf_eval_1",
        workflow_name="Eval Pipeline",
        status=status,
        stage_results=[
            StageRunResult(stage_id="memory", status=StageRunStatus.completed),
            StageRunResult(stage_id="rag", status=StageRunStatus.completed),
            StageRunResult(stage_id="agents", status=StageRunStatus.completed),
            StageRunResult(
                stage_id="validation",
                status=StageRunStatus.failed,
                error_message="missing insights",
                metadata={"retry_count": 1},
            ),
        ],
        errors=[],
    )


def test_workflow_evaluation_metrics():
    metrics = evaluate_workflow(
        {
            "status": "completed",
            "stage_results": [
                {"stage_id": "a", "status": "completed"},
                {"stage_id": "b", "status": "completed"},
            ],
            "errors": [],
        }
    )
    names = {m.name for m in metrics}
    assert names == {"completion", "failure_rate", "retries"}
    assert all(m.category == EvaluationCategory.workflow for m in metrics)
    assert metrics[0].score >= 0.9


def test_agent_and_tool_scoring():
    artifact = {
        "agent_executions": [
            {
                "execution_id": "ae1",
                "status": "completed",
                "tool_request_ids": ["data_profiling", "insight_generation"],
                "result": {"tool_results": [{"status": "ok"}, {"status": "ok"}]},
                "metadata": {},
            }
        ],
        "agent_results": {"Data Analyst Agent": {"ok": True}},
        "plan_result": {
            "validated": True,
            "steps": [
                {"tool_name": "data_profiling"},
                {"tool_name": "insight_generation"},
            ],
        },
    }
    agents = evaluate_agents(artifact)
    tools = evaluate_tools(artifact)
    assert any(m.name == "planning_quality" and m.score >= 0.8 for m in agents)
    assert any(m.name == "execution_success" and m.score >= 0.5 for m in tools)


def test_rag_and_llm_scoring():
    artifact = {
        "rag_chunk_ids": ["c1", "c2"],
        "rag_snippets": [
            {"relevance": 0.9, "source": "playbook", "content": "North decline guidance"},
            {"relevance": 0.8, "source": "kpi_guide", "content": "Inspect regional KPIs"},
        ],
        "rag_sources": ["playbook", "kpi_guide"],
        "rag_context_text": "- (0.900) North decline guidance\n- (0.800) Inspect regional KPIs",
        "result": {
            "answer": "North region drove the decline.",
            "insights": ["North revenue down"],
            "recommendations": ["Investigate North sales execution"],
            "structured_output": {
                "answer": "North region drove the decline.",
                "insights": ["North revenue down"],
                "recommendations": ["Investigate North sales execution"],
            },
            "validation_status": "valid",
            "workflow_results": {"status": "completed", "rag_chunk_ids": ["c1", "c2"]},
            "metadata": {"rag_chunk_ids": ["c1", "c2"]},
        },
    }
    rag = evaluate_rag(artifact)
    llm = evaluate_llm(artifact)
    assert any(m.name == "retrieval_relevance" and m.score >= 0.7 for m in rag)
    assert any(m.name == "source_diversity" and m.score >= 0.7 for m in rag)
    assert any(m.name == "structured_output_validity" and m.score == 1.0 for m in llm)
    assert any(m.name == "schema_compliance" and m.score == 1.0 for m in llm)


def test_evaluate_workflow_run_and_export():
    execution = _sample_execution()
    run = evaluate_workflow_run(
        execution,
        context={
            "agent_executions": [{"status": "completed", "tool_request_ids": ["validation"]}],
            "agent_results": {"Validation Agent": {"ok": True}},
            "plan_result": {"steps": [{"tool_name": "validation"}], "validated": True},
            "rag_chunk_ids": ["chunk_1"],
            "rag_snippets": [{"relevance": 0.7, "source": "doc_a", "content": "guideline text here"}],
            "rag_sources": ["doc_a"],
            "rag_context_text": "guideline text here for quality",
            "memory_ids": ["mem_1"],
            "memory_snippets": [{"content": "prior revenue analysis"}],
            "analyst_answer": "Revenue declined in North.",
            "analyst_insights": ["North is weakest"],
            "analyst_recommendations": ["Investigate North region"],
        },
        session_id="asess_test",
    )
    assert run.status == EvaluationStatus.completed
    assert run.evaluation_id
    assert 0.0 <= run.overall_score <= 1.0
    assert run.grade in {"A", "B", "C", "D", "F"}
    assert run.report is not None
    assert len(run.metrics) >= 10

    exported = export_evaluation(run)
    assert exported["evaluation_id"] == run.evaluation_id
    assert "metrics_summary" in exported
    assert "score_breakdown" in exported
    assert "report" in exported
    assert exported["read_only"] is True

    summary = evaluation_summary(run.evaluation_id)
    assert summary["found"] is True
    assert get_evaluation(run.evaluation_id) is not None


def test_evaluate_session_read_only():
    session = {
        "session_id": "asess_1",
        "workflow_id": "wf_1",
        "status": "completed",
        "user_query": "Analyze revenue decline",
        "context": {
            "rag_chunk_ids": ["r1"],
            "memory_ids": ["m1"],
            "rag_context_text": "North region often drives decline.",
            "rag_snippets": [{"relevance": 0.8, "source": "guide", "content": "North region"}],
        },
        "result": {
            "answer": "North region caused the decline.",
            "insights": ["North down vs East"],
            "recommendations": ["Focus remediation on North"],
            "validation_status": "valid",
            "structured_output": {
                "answer": "North region caused the decline.",
                "insights": ["North down vs East"],
                "recommendations": ["Focus remediation on North"],
            },
            "workflow_results": {
                "status": "completed",
                "stage_count": 4,
                "agent_executions": [{"status": "completed", "tool_request_ids": ["insight_generation"]}],
                "agent_results": {"Insight Agent": {"ok": True}},
                "plan_result": {
                    "validated": True,
                    "steps": [{"tool_name": "insight_generation"}, {"tool_name": "validation"}],
                },
                "rag_chunk_ids": ["r1"],
                "memory_ids": ["m1"],
            },
            "metadata": {"rag_chunk_ids": ["r1"]},
        },
    }
    original_answer = session["result"]["answer"]
    run = evaluate_session(session)
    assert run.session_id == "asess_1"
    assert session["result"]["answer"] == original_answer  # read-only
    assert run.overall_score > 0
