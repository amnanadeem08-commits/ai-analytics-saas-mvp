from __future__ import annotations

from backend.services.llm_service import reset_llm_provider
from backend.services.tool_registry_service import ensure_builtin_tools
from backend.services.tool_selection_service import (
    rank_tools,
    select_tool,
    validate_tool_selection,
)


def setup_function():
    reset_llm_provider()
    ensure_builtin_tools(reset=True)


def test_select_kpi_tool():
    result = select_tool("Find important KPIs", agent_role="data_analyst")
    assert result["tool_id"] == "kpi_detection"
    assert result["valid"] is True


def test_select_forecast_explanation_tool():
    result = select_tool("Explain forecast results", agent_role="reporting")
    assert result["tool_id"] == "forecast_explanation"
    assert result["valid"] is True


def test_rank_tools_orders_by_relevance():
    ranked = rank_tools("Validate insight quality and consistency", agent_role="validation")
    assert ranked
    assert ranked[0]["tool_id"] == "validation"
    assert ranked[0]["score"] >= ranked[-1]["score"]


def test_validate_tool_selection():
    assert validate_tool_selection("kpi_detection")["valid"] is True
    assert validate_tool_selection("missing_tool")["valid"] is False
    assert validate_tool_selection(
        "kpi_detection",
        allowed_tools=["validation"],
    )["valid"] is False
