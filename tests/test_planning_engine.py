from __future__ import annotations

from backend.models.planning_models import PlanStatus, PlanStep, PlanStepStatus
from backend.models.tool_models import ToolDefinition
from backend.services.llm_service import reset_llm_provider
from backend.services.planning_service import (
    add_plan_step,
    clear_plans,
    create_plan,
    execute_plan,
    get_plan_status,
    plan_summary,
    validate_plan,
)
from backend.services.tool_registry_service import ensure_builtin_tools, register_tool


def setup_function():
    reset_llm_provider()
    ensure_builtin_tools(reset=True)
    clear_plans()


def test_plan_creation_and_validation():
    plan = create_plan(
        "Analyze customer revenue decline",
        agent_name="multi_agent_planner",
    )
    assert plan.plan_id
    assert plan.task
    assert len(plan.steps) >= 3
    tools = [s.tool_name for s in plan.steps]
    assert "data_profiling" in tools
    assert "insight_generation" in tools
    assert "validation" in tools
    assert validate_plan(plan)["valid"] is True
    summary = plan_summary(plan)
    assert summary["step_count"] == len(plan.steps)
    assert get_plan_status(plan.plan_id) == PlanStatus.ready


def test_add_plan_step():
    plan = create_plan("Find important KPIs", agent_role="data_analyst")
    updated = add_plan_step(
        plan,
        PlanStep(
            step_id="step_extra",
            description="Extra governance check",
            agent_name="Reporting Agent",
            tool_name="governance_validation",
            expected_output="governance",
        ),
    )
    assert any(s.step_id == "step_extra" for s in updated.steps)
    assert validate_plan(updated)["valid"] is True


def test_execute_plan_success():
    plan = create_plan(
        "Find important KPIs",
        agent_name="Data Analyst Agent",
        agent_role="data_analyst",
        available_tools=["kpi_detection", "data_profiling"],
    )
    updated, result = execute_plan(plan, context={"dataset_id": "sales_q1"})
    assert result.status in {PlanStatus.completed, PlanStatus.partial}
    assert result.completed_steps
    assert updated.status in {PlanStatus.completed, PlanStatus.partial}


def test_failed_step_with_alternative_recovery():
    def boom(arguments, context):
        raise RuntimeError("primary failed")

    def ok(arguments, context):
        return {"tool": "alt_ok", "ok": True}

    register_tool(
        ToolDefinition(
            tool_id="primary_fail_tool",
            name="Primary Fail",
            description="Always fails",
            input_schema={},
            output_schema={},
            permission_flag="internal.read",
        ),
        boom,
    )
    register_tool(
        ToolDefinition(
            tool_id="alt_ok_tool",
            name="Alt OK",
            description="Always works",
            input_schema={},
            output_schema={},
            permission_flag="internal.read",
        ),
        ok,
    )
    plan = create_plan(
        "custom recovery task",
        steps=[
            PlanStep(
                step_id="step_1",
                description="Try primary then alternative",
                agent_name="custom",
                tool_name="primary_fail_tool",
                alternative_tools=["alt_ok_tool"],
                max_retries=0,
                expected_output="ok",
            )
        ],
        available_tools=["primary_fail_tool", "alt_ok_tool"],
    )
    updated, result = execute_plan(plan, allow_alternatives=True, stop_on_error=True)
    assert "step_1" in result.completed_steps
    assert updated.steps[0].tool_name == "alt_ok_tool"
    assert updated.steps[0].status in {PlanStepStatus.completed, PlanStepStatus.retried}


def test_missing_tool_fails_gracefully():
    plan = create_plan(
        "broken",
        steps=[
            PlanStep(
                step_id="step_1",
                description="Missing tool",
                agent_name="custom",
                tool_name="does_not_exist",
                max_retries=0,
            )
        ],
        available_tools=["does_not_exist"],
    )
    # Bypass validate by executing directly
    updated, result = execute_plan(plan, stop_on_error=True, allow_alternatives=False)
    assert result.status == PlanStatus.failed
    assert "step_1" in result.failed_steps
    assert updated.steps[0].status == PlanStepStatus.failed
