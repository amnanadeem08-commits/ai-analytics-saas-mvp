from __future__ import annotations

from backend.models.forecast_capability_models import (
    FORECAST_CAPABILITY_FUTURE_EXTENSION_KEYS,
    CapabilityStatus,
    CapabilityType,
    ForecastCapability,
)
from backend.services.forecast_capability_service import (
    build_capability_registry,
    find_capability,
    find_dependencies,
    find_dependents,
    list_capabilities,
    register_capability,
    registry_statistics,
    registry_summary,
    validate_registry,
)

EXPECTED_IDS = {
    "forecast_adapter_framework",
    "forecast_pipeline",
    "prediction_engine",
    "prediction_validation",
    "future_statistical_forecast",
    "future_machine_learning_forecast",
    "future_deep_learning_forecast",
    "future_ensemble_forecast",
}


def test_registry_creation_and_registration():
    registry = build_capability_registry()
    ids = {c.capability_id for c in registry.capabilities}
    assert EXPECTED_IDS.issubset(ids)
    assert len(registry.capabilities) == 8
    assert validate_registry(registry)["valid"] is True

    custom = ForecastCapability(
        capability_id="custom_cap",
        capability_name="Custom Cap",
        capability_type=CapabilityType.custom,
        status=CapabilityStatus.experimental,
        dependencies=["prediction_engine"],
        limitations=["test"],
    )
    updated = register_capability(registry, custom)
    assert find_capability(registry, "custom_cap") is None
    assert find_capability(updated, "custom_cap") is not None


def test_lookup_listing_dependencies():
    registry = build_capability_registry()
    assert find_capability(registry, "prediction_engine") is not None
    available = list_capabilities(registry, status=CapabilityStatus.available)
    assert {c.capability_id for c in available} >= {
        "forecast_adapter_framework",
        "forecast_pipeline",
        "prediction_engine",
        "prediction_validation",
    }
    planned = list_capabilities(registry, status="planned")
    assert any(c.capability_id == "future_statistical_forecast" for c in planned)

    deps = find_dependencies(registry, "forecast_pipeline")
    assert "forecast_adapter_framework" in deps
    dependents = find_dependents(registry, "prediction_engine")
    assert "prediction_validation" in dependents
    assert "future_statistical_forecast" in dependents


def test_statistics_and_summary():
    registry = build_capability_registry()
    stats = registry_statistics(registry)
    assert stats.total_capabilities == 8
    assert stats.active_capabilities == 4
    assert stats.planned_capabilities >= 2
    assert stats.experimental_capabilities >= 1
    assert stats.dependency_count > 0
    assert stats.capability_type_breakdown[CapabilityType.adapter.value] == 1

    summary = registry_summary(registry)
    assert summary.total_capabilities == 8
    assert summary.available == 4
    assert summary.overall_health == "healthy"
    assert summary.dependency_count == stats.dependency_count


def test_validation_duplicates_and_cycles():
    registry = build_capability_registry()
    assert validate_registry(registry)["valid"] is True

    empty = build_capability_registry(include_builtins=False)
    assert validate_registry(empty)["valid"] is False
    assert any("Empty registry" in i for i in validate_registry(empty)["issues"])

    dup = registry.model_copy(deep=True)
    dup.capabilities = list(dup.capabilities) + [dup.capabilities[0].model_copy(deep=True)]
    assert any("Duplicate capability_id" in i for i in validate_registry(dup)["issues"])

    a = ForecastCapability(
        capability_id="a",
        capability_name="A",
        capability_type=CapabilityType.custom,
        status=CapabilityStatus.planned,
        dependencies=["b"],
    )
    b = ForecastCapability(
        capability_id="b",
        capability_name="B",
        capability_type=CapabilityType.custom,
        status=CapabilityStatus.planned,
        dependencies=["a"],
    )
    cyclic = build_capability_registry(include_builtins=False)
    cyclic = register_capability(cyclic, a)
    cyclic = register_capability(cyclic, b)
    result = validate_registry(cyclic)
    assert result["valid"] is False
    assert result["circular_dependencies"]
    assert any("Circular dependency" in i for i in result["issues"])

    missing = register_capability(
        build_capability_registry(include_builtins=False),
        ForecastCapability(
            capability_id="x",
            capability_name="X",
            capability_type=CapabilityType.custom,
            status=CapabilityStatus.planned,
            dependencies=["missing"],
        ),
    )
    assert any("Missing dependency" in i for i in validate_registry(missing)["issues"])


def test_future_extension_buckets():
    registry = build_capability_registry()
    for key in FORECAST_CAPABILITY_FUTURE_EXTENSION_KEYS:
        assert key in registry.metadata.future_extensions
        assert registry.metadata.future_extensions[key] == {}
    assert "arima" in registry.metadata.future_extensions
    assert "prophet" in registry.metadata.future_extensions
    assert "experiment_tracking" in registry.metadata.future_extensions


def test_immutability():
    registry = build_capability_registry()
    snapshot = registry.model_dump()
    found = find_capability(registry, "prediction_engine")
    assert found is not None
    found.capability_name = "mutated"
    listed = list_capabilities(registry)
    listed[0].capability_name = "mutated_list"
    find_dependencies(registry, "forecast_pipeline")
    find_dependents(registry, "prediction_engine")
    registry_statistics(registry)
    registry_summary(registry)
    validate_registry(registry)
    register_capability(
        registry,
        ForecastCapability(
            capability_id="temp",
            capability_name="Temp",
            capability_type=CapabilityType.custom,
            status=CapabilityStatus.planned,
            dependencies=["prediction_engine"],
        ),
    )
    assert registry.model_dump() == snapshot
