from __future__ import annotations

from backend.models.forecast_adapter_models import (
    FORECAST_ADAPTER_FUTURE_EXTENSION_KEYS,
    FORECAST_ADAPTER_INTERFACE_METHODS,
    FORECAST_FUTURE_ADAPTER_KEYS,
    AdapterExecutionStatus,
    AdapterType,
    ForecastAdapter,
    ForecastAdapterInterfaceSpec,
    ForecastAdapterProtocol,
)
from backend.services.forecast_adapter_service import (
    adapter_statistics,
    adapters_by_domain,
    adapters_by_type,
    build_adapter_registry,
    find_adapter,
    list_adapters,
    register_adapter,
    validate_adapter,
    validate_adapter_registry,
)

EXPECTED_TYPE_ADAPTERS = {
    "statistical_adapter",
    "machine_learning_adapter",
    "deep_learning_adapter",
    "llm_forecasting_adapter",
    "rule_based_adapter",
    "hybrid_adapter",
    "custom_adapter",
}


def test_adapter_registration_and_registry():
    registry = build_adapter_registry()
    ids = {adapter.adapter_id for adapter in registry.adapters}
    assert EXPECTED_TYPE_ADAPTERS.issubset(ids)
    assert len(registry.adapters) == 7
    assert validate_adapter_registry(registry)["valid"] is True

    custom = ForecastAdapter(
        adapter_id="plugin_adapter",
        adapter_name="Plugin Adapter",
        adapter_type=AdapterType.custom,
        description="Test plugin",
        supported_domains=["Custom"],
        supported_prediction_types=["Custom"],
        required_inputs=["payload"],
        expected_outputs=["prediction_collection"],
        execution_status=AdapterExecutionStatus.experimental,
        metadata={"note": "catalog-only"},
    )
    updated = register_adapter(registry, custom)
    assert find_adapter(registry, "plugin_adapter") is None
    assert find_adapter(updated, "plugin_adapter") is not None
    assert find_adapter(updated, "plugin_adapter").metadata["note"] == "catalog-only"


def test_discovery_and_grouping():
    registry = build_adapter_registry()
    listed = list_adapters(registry)
    assert len(listed) == 7

    ml = adapters_by_type(registry, AdapterType.machine_learning)
    assert len(ml) == 1
    assert ml[0].adapter_id == "machine_learning_adapter"

    sales = adapters_by_domain(registry, "Sales")
    assert {a.adapter_id for a in sales} >= {
        "statistical_adapter",
        "machine_learning_adapter",
        "rule_based_adapter",
    }

    available = list_adapters(registry, execution_status=AdapterExecutionStatus.available)
    assert any(a.adapter_id == "rule_based_adapter" for a in available)


def test_validation_and_statistics():
    registry = build_adapter_registry()
    for adapter in registry.adapters:
        assert validate_adapter(adapter)["valid"] is True

    stats = adapter_statistics(registry)
    assert stats.total_adapters == 7
    assert stats.by_type[AdapterType.statistical.value] == 1
    assert stats.confidence_supported_count >= 1
    assert stats.training_supported_count >= 1
    assert stats.validation_supported_count >= 1

    broken = ForecastAdapter(
        adapter_id="broken",
        adapter_name="Broken",
        adapter_type=AdapterType.custom,
        dependencies=["missing_dep"],
        interface=ForecastAdapterInterfaceSpec(methods=["prepare"]),
    )
    updated = register_adapter(registry, broken)
    result = validate_adapter_registry(updated)
    assert result["valid"] is False
    assert any("Missing dependency" in issue or "Missing interface" in issue for issue in result["issues"])


def test_interface_definitions():
    registry = build_adapter_registry()
    assert list(registry.interface_contract.methods) == list(FORECAST_ADAPTER_INTERFACE_METHODS)
    for adapter in registry.adapters:
        assert set(FORECAST_ADAPTER_INTERFACE_METHODS).issubset(set(adapter.interface.methods))

    # Protocol is a structural contract only — no concrete forecasting class required.
    assert hasattr(ForecastAdapterProtocol, "prepare")
    assert hasattr(ForecastAdapterProtocol, "predict")
    assert hasattr(ForecastAdapterProtocol, "validate")
    assert hasattr(ForecastAdapterProtocol, "explain")
    assert hasattr(ForecastAdapterProtocol, "cleanup")


def test_future_buckets():
    registry = build_adapter_registry()
    for key in FORECAST_ADAPTER_FUTURE_EXTENSION_KEYS:
        assert key in registry.metadata.future_extensions
        assert registry.metadata.future_extensions[key] == {}
    for key in FORECAST_FUTURE_ADAPTER_KEYS:
        assert key in registry.metadata.future_adapters
        assert registry.metadata.future_adapters[key] == {}
    assert "arima" in registry.metadata.future_adapters
    assert "prophet" in registry.metadata.future_adapters
    assert "lstm" in registry.metadata.future_adapters
    assert "backtesting" in registry.metadata.future_extensions


def test_immutability():
    registry = build_adapter_registry()
    snapshot = registry.model_dump()
    found = find_adapter(registry, "statistical_adapter")
    assert found is not None
    found.adapter_name = "mutated"
    listed = list_adapters(registry)
    listed[0].adapter_name = "mutated_list"
    adapters_by_type(registry, AdapterType.hybrid)
    adapters_by_domain(registry, "Finance")
    adapter_statistics(registry)
    validate_adapter_registry(registry)
    register_adapter(
        registry,
        ForecastAdapter(
            adapter_id="temp",
            adapter_name="Temp",
            adapter_type=AdapterType.custom,
        ),
    )
    assert registry.model_dump() == snapshot
