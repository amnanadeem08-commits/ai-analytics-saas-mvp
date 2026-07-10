from __future__ import annotations

from backend.models.intelligence_orchestrator_models import (
    INTELLIGENCE_ORCHESTRATOR_FUTURE_EXTENSION_KEYS,
    OrchestrationStage,
    StageStatus,
)
from backend.services.intelligence_orchestrator_service import (
    build_orchestrator,
    execution_graph,
    execution_order,
    find_dependencies,
    find_dependents,
    find_stage,
    orchestrator_statistics,
    register_stage,
    validate_orchestrator,
)

EXPECTED_STAGE_IDS = [
    "insights",
    "validation",
    "decision",
    "root_cause",
    "executive_reasoning",
    "storyboard",
    "bundle",
    "registry",
    "ai_analyst",
    "prediction",
    "prediction_validation",
    "forecast_adapter",
    "pipeline",
    "capability_registry",
    "dataset_readiness",
    "scenario_registry",
    "explainability",
    "governance",
]


def test_orchestrator_creation_and_registration():
    orchestrator = build_orchestrator()
    ids = [s.stage_id for s in orchestrator.stages]
    assert ids == EXPECTED_STAGE_IDS
    assert validate_orchestrator(orchestrator)["valid"] is True
    assert orchestrator.metadata is not None
    assert orchestrator.schema_version

    extra = OrchestrationStage(
        stage_id="custom_stage",
        stage_name="Custom Stage",
        dependencies=["governance"],
        optional_dependencies=["explainability"],
        execution_order=190,
        enabled=True,
        status=StageStatus.experimental,
        metadata={"note": "extension slot"},
    )
    updated = register_stage(orchestrator, extra)
    assert find_stage(orchestrator, "custom_stage") is None
    assert find_stage(updated, "custom_stage") is not None
    assert find_stage(updated, "custom_stage").metadata["note"] == "extension slot"


def test_execution_graph_and_order():
    orchestrator = build_orchestrator()
    order = execution_order(orchestrator)
    assert order == EXPECTED_STAGE_IDS
    assert order[0] == "insights"
    assert order[-1] == "governance"

    graph = execution_graph(orchestrator)
    assert graph["ordered_stage_ids"] == EXPECTED_STAGE_IDS
    assert len(graph["nodes"]) == 18
    assert any(e["from"] == "insights" and e["to"] == "validation" for e in graph["edges"])
    assert any(
        e["kind"] == "optional" and e["to"] == "root_cause" for e in graph["edges"]
    )


def test_dependencies_dependents_and_optional():
    orchestrator = build_orchestrator()
    assert find_dependencies(orchestrator, "validation") == ["insights"]
    assert "decision" in find_dependents(orchestrator, "validation")

    deps = find_dependencies(orchestrator, "root_cause", include_optional=True)
    assert "decision" in deps
    assert "validation" in deps

    optional_only = find_dependencies(orchestrator, "root_cause", include_optional=False)
    assert optional_only == ["decision"]

    dependents = find_dependents(orchestrator, "explainability", include_optional=True)
    assert "governance" in dependents


def test_validation_missing_stages_and_cycles():
    orchestrator = build_orchestrator()
    assert validate_orchestrator(orchestrator)["valid"] is True

    empty = build_orchestrator(include_builtins=False)
    assert validate_orchestrator(empty)["valid"] is False
    assert any("Empty orchestrator" in i for i in validate_orchestrator(empty)["issues"])

    broken = register_stage(
        build_orchestrator(include_builtins=False),
        OrchestrationStage(
            stage_id="orphan",
            stage_name="Orphan",
            dependencies=["missing_required"],
            optional_dependencies=["missing_optional"],
            execution_order=1,
            status=StageStatus.planned,
        ),
    )
    result = validate_orchestrator(broken)
    assert result["valid"] is False
    assert result["missing_required_dependencies"]
    assert result["missing_optional_dependencies"]
    assert any("Missing required dependency" in i for i in result["issues"])
    assert any("Missing optional dependency" in i for i in result["issues"])

    a = OrchestrationStage(
        stage_id="a",
        stage_name="A",
        dependencies=["b"],
        execution_order=1,
        status=StageStatus.planned,
    )
    b = OrchestrationStage(
        stage_id="b",
        stage_name="B",
        dependencies=["a"],
        execution_order=2,
        status=StageStatus.planned,
    )
    cyclic = build_orchestrator(include_builtins=False)
    cyclic = register_stage(cyclic, a)
    cyclic = register_stage(cyclic, b)
    cyclic_result = validate_orchestrator(cyclic)
    assert cyclic_result["valid"] is False
    assert cyclic_result["circular_dependencies"]


def test_statistics():
    orchestrator = build_orchestrator()
    stats = orchestrator_statistics(orchestrator)
    assert stats.total_stages == 18
    assert stats.enabled_stages == 18
    assert stats.disabled_stages == 0
    assert stats.available_stages == 18
    assert stats.dependency_count > 0
    assert stats.optional_dependency_count > 0
    assert stats.max_execution_order == 180


def test_future_extension_buckets():
    orchestrator = build_orchestrator()
    for key in INTELLIGENCE_ORCHESTRATOR_FUTURE_EXTENSION_KEYS:
        assert key in orchestrator.metadata.future_extensions
        assert orchestrator.metadata.future_extensions[key] == {}
    assert "runtime" in orchestrator.metadata.future_extensions
    assert "agents" in orchestrator.metadata.future_extensions
    assert "llm" in orchestrator.metadata.future_extensions
    assert "parallel_execution" in orchestrator.metadata.future_extensions


def test_immutability():
    orchestrator = build_orchestrator()
    snapshot = orchestrator.model_dump()
    found = find_stage(orchestrator, "insights")
    assert found is not None
    found.stage_name = "mutated"
    graph = execution_graph(orchestrator)
    graph["nodes"][0]["stage_name"] = "mutated_graph"
    execution_order(orchestrator)
    find_dependencies(orchestrator, "prediction")
    find_dependents(orchestrator, "insights")
    orchestrator_statistics(orchestrator)
    validate_orchestrator(orchestrator)
    register_stage(
        orchestrator,
        OrchestrationStage(
            stage_id="temp",
            stage_name="Temp",
            dependencies=["governance"],
            execution_order=999,
            status=StageStatus.planned,
        ),
    )
    assert orchestrator.model_dump() == snapshot
