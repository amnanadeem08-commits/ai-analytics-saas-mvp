from __future__ import annotations

from backend.models.forecast_scenario_models import (
    FORECAST_SCENARIO_FUTURE_EXTENSION_KEYS,
    ForecastScenario,
    ScenarioStatus,
    ScenarioType,
)
from backend.services.forecast_scenario_service import (
    build_scenario_registry,
    find_dependencies,
    find_dependents,
    find_scenario,
    list_scenarios,
    register_scenario,
    scenario_statistics,
    scenario_summary,
    validate_registry,
)

EXPECTED_IDS = {
    "baseline",
    "expected",
    "optimistic",
    "pessimistic",
    "best_case",
    "worst_case",
    "custom",
}


def test_registry_creation_and_registration():
    registry = build_scenario_registry()
    ids = {s.scenario_id for s in registry.scenarios}
    assert EXPECTED_IDS.issubset(ids)
    assert len(registry.scenarios) == 7
    assert validate_registry(registry)["valid"] is True

    extra = ForecastScenario(
        scenario_id="extra_custom",
        scenario_name="Extra Custom",
        scenario_type=ScenarioType.custom,
        status=ScenarioStatus.experimental,
        assumptions=["Caller-defined assumption."],
        limitations=["No execution."],
        dependencies=["baseline"],
    )
    updated = register_scenario(registry, extra)
    assert find_scenario(registry, "extra_custom") is None
    assert find_scenario(updated, "extra_custom") is not None


def test_lookup_listing_dependencies():
    registry = build_scenario_registry()
    assert find_scenario(registry, "baseline") is not None
    available = list_scenarios(registry, status=ScenarioStatus.available)
    assert {s.scenario_id for s in available} >= {
        "baseline",
        "expected",
        "optimistic",
        "pessimistic",
    }
    planned = list_scenarios(registry, status="planned")
    assert {s.scenario_id for s in planned} >= {"best_case", "worst_case"}

    deps = find_dependencies(registry, "optimistic")
    assert "baseline" in deps
    assert "expected" in deps
    dependents = find_dependents(registry, "baseline")
    assert "expected" in dependents
    assert "custom" in dependents


def test_statistics_and_summary():
    registry = build_scenario_registry()
    stats = scenario_statistics(registry)
    assert stats.total_scenarios == 7
    assert stats.available == 4
    assert stats.planned == 2
    assert stats.experimental == 1
    assert stats.custom == 1
    assert stats.dependency_count > 0

    summary = scenario_summary(registry)
    assert summary.scenario_count == 7
    assert summary.available == 4
    assert summary.overall_health == "healthy"
    assert summary.dependency_count == stats.dependency_count


def test_validation_duplicates_and_cycles():
    registry = build_scenario_registry()
    assert validate_registry(registry)["valid"] is True

    empty = build_scenario_registry(include_builtins=False)
    assert validate_registry(empty)["valid"] is False
    assert any("Empty registry" in i for i in validate_registry(empty)["issues"])

    dup = registry.model_copy(deep=True)
    dup.scenarios = list(dup.scenarios) + [dup.scenarios[0].model_copy(deep=True)]
    assert any("Duplicate scenario_id" in i for i in validate_registry(dup)["issues"])

    missing_fields = ForecastScenario(
        scenario_id="incomplete",
        scenario_name="Incomplete",
        scenario_type=ScenarioType.custom,
        status=ScenarioStatus.planned,
        assumptions=[],
        limitations=[],
    )
    incomplete_reg = register_scenario(build_scenario_registry(include_builtins=False), missing_fields)
    issues = validate_registry(incomplete_reg)["issues"]
    assert any("Missing assumptions" in i for i in issues)
    assert any("Missing limitations" in i for i in issues)

    a = ForecastScenario(
        scenario_id="a",
        scenario_name="A",
        scenario_type=ScenarioType.custom,
        status=ScenarioStatus.planned,
        assumptions=["a"],
        limitations=["a"],
        dependencies=["b"],
    )
    b = ForecastScenario(
        scenario_id="b",
        scenario_name="B",
        scenario_type=ScenarioType.custom,
        status=ScenarioStatus.planned,
        assumptions=["b"],
        limitations=["b"],
        dependencies=["a"],
    )
    cyclic = build_scenario_registry(include_builtins=False)
    cyclic = register_scenario(cyclic, a)
    cyclic = register_scenario(cyclic, b)
    result = validate_registry(cyclic)
    assert result["valid"] is False
    assert result["circular_dependencies"]
    assert any("Circular dependency" in i for i in result["issues"])

    broken = register_scenario(
        build_scenario_registry(include_builtins=False),
        ForecastScenario(
            scenario_id="x",
            scenario_name="X",
            scenario_type=ScenarioType.custom,
            status=ScenarioStatus.planned,
            assumptions=["x"],
            limitations=["x"],
            dependencies=["missing"],
        ),
    )
    assert any("Broken dependency" in i for i in validate_registry(broken)["issues"])


def test_future_extension_buckets():
    registry = build_scenario_registry()
    for key in FORECAST_SCENARIO_FUTURE_EXTENSION_KEYS:
        assert key in registry.metadata.future_extensions
        assert registry.metadata.future_extensions[key] == {}
    assert "monte_carlo" in registry.metadata.future_extensions
    assert "what_if" in registry.metadata.future_extensions
    assert "digital_twin" in registry.metadata.future_extensions


def test_immutability():
    registry = build_scenario_registry()
    snapshot = registry.model_dump()
    found = find_scenario(registry, "baseline")
    assert found is not None
    found.scenario_name = "mutated"
    listed = list_scenarios(registry)
    listed[0].scenario_name = "mutated_list"
    find_dependencies(registry, "optimistic")
    find_dependents(registry, "baseline")
    scenario_statistics(registry)
    scenario_summary(registry)
    validate_registry(registry)
    register_scenario(
        registry,
        ForecastScenario(
            scenario_id="temp",
            scenario_name="Temp",
            scenario_type=ScenarioType.custom,
            status=ScenarioStatus.planned,
            assumptions=["t"],
            limitations=["t"],
            dependencies=["baseline"],
        ),
    )
    assert registry.model_dump() == snapshot
