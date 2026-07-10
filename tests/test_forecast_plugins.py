from __future__ import annotations

from backend.models.forecast_plugin_models import (
    FORECAST_FUTURE_PLUGIN_KEYS,
    FORECAST_PLUGIN_FUTURE_EXTENSION_KEYS,
    FORECAST_PLUGIN_INTERFACE_METHODS,
    ForecastPlugin,
    ForecastPluginInterfaceSpec,
    ForecastPluginProtocol,
    PluginCapability,
    PluginCompatibility,
    PluginExecutionState,
    PluginType,
)
from backend.services.forecast_plugin_service import (
    build_plugin_registry,
    find_plugin,
    list_plugins,
    plugin_statistics,
    plugins_by_capability,
    plugins_by_domain,
    plugins_by_type,
    register_plugin,
    unregister_plugin,
    validate_plugin,
    validate_plugin_registry,
)

EXPECTED_TYPE_PLUGINS = {
    "statistical_plugin",
    "machine_learning_plugin",
    "deep_learning_plugin",
    "foundation_model_plugin",
    "hybrid_plugin",
    "trading_plugin",
    "business_plugin",
    "custom_plugin",
}


def test_plugin_registration_and_registry():
    registry = build_plugin_registry()
    ids = {plugin.plugin_id for plugin in registry.plugins}
    assert EXPECTED_TYPE_PLUGINS.issubset(ids)
    assert len(registry.plugins) == 8
    assert validate_plugin_registry(registry)["valid"] is True

    custom = ForecastPlugin(
        plugin_id="extra_plugin",
        plugin_name="Extra Plugin",
        plugin_type=PluginType.custom,
        description="Test plug-in",
        supported_domains=["Custom"],
        supported_prediction_types=["Custom"],
        execution_state=PluginExecutionState.experimental,
        metadata={"note": "catalog-only"},
    )
    updated = register_plugin(registry, custom)
    assert find_plugin(registry, "extra_plugin") is None
    assert find_plugin(updated, "extra_plugin") is not None
    assert find_plugin(updated, "extra_plugin").metadata["note"] == "catalog-only"

    removed = unregister_plugin(updated, "extra_plugin")
    assert find_plugin(removed, "extra_plugin") is None
    assert find_plugin(updated, "extra_plugin") is not None


def test_discovery_capabilities_and_grouping():
    registry = build_plugin_registry()
    assert len(list_plugins(registry)) == 8

    ml = plugins_by_type(registry, PluginType.machine_learning)
    assert len(ml) == 1
    assert ml[0].plugin_id == "machine_learning_plugin"

    sales = plugins_by_domain(registry, "Sales")
    assert {p.plugin_id for p in sales} >= {
        "statistical_plugin",
        "machine_learning_plugin",
        "business_plugin",
    }

    multivariate = plugins_by_capability(registry, PluginCapability.multivariate)
    assert all(p.supports_multivariate for p in multivariate)
    assert any(p.plugin_id == "deep_learning_plugin" for p in multivariate)

    online = plugins_by_capability(registry, "online_learning")
    assert all(p.supports_online_learning for p in online)

    available = list_plugins(registry, execution_state=PluginExecutionState.available)
    assert any(p.plugin_id == "business_plugin" for p in available)


def test_compatibility_validation_and_statistics():
    registry = build_plugin_registry()
    for plugin in registry.plugins:
        result = validate_plugin(plugin)
        assert result["valid"] is True
        assert result["fully_compatible"] is True
        assert plugin.compatibility.adapter_compatible
        assert plugin.compatibility.prediction_compatible
        assert plugin.compatibility.validation_compatible
        assert plugin.compatibility.registry_compatible
        assert plugin.compatibility.bundle_compatible

    stats = plugin_statistics(registry)
    assert stats.total_plugins == 8
    assert stats.by_type[PluginType.statistical.value] == 1
    assert stats.fully_compatible_count == 8
    assert stats.probabilistic_count >= 1
    assert stats.explainability_count >= 1

    broken = ForecastPlugin(
        plugin_id="broken_plugin",
        plugin_name="Broken",
        plugin_type=PluginType.custom,
        dependencies=["missing_dep"],
        interface=ForecastPluginInterfaceSpec(methods=["initialize", "predict"]),
        compatibility=PluginCompatibility(adapter_compatible=False),
    )
    updated = register_plugin(registry, broken)
    result = validate_plugin_registry(updated)
    assert result["valid"] is False
    assert any(
        "Missing dependency" in issue or "Missing interface" in issue for issue in result["issues"]
    )
    assert validate_plugin(broken)["fully_compatible"] is False


def test_lifecycle_interface():
    registry = build_plugin_registry()
    assert list(registry.interface_contract.methods) == list(FORECAST_PLUGIN_INTERFACE_METHODS)
    for plugin in registry.plugins:
        assert set(FORECAST_PLUGIN_INTERFACE_METHODS).issubset(set(plugin.interface.methods))

    for method in FORECAST_PLUGIN_INTERFACE_METHODS:
        assert hasattr(ForecastPluginProtocol, method)


def test_reserved_plugins_and_infrastructure():
    registry = build_plugin_registry()
    for key in FORECAST_PLUGIN_FUTURE_EXTENSION_KEYS:
        assert key in registry.metadata.future_extensions
        assert registry.metadata.future_extensions[key] == {}
    for key in FORECAST_FUTURE_PLUGIN_KEYS:
        assert key in registry.metadata.future_plugins
        assert registry.metadata.future_plugins[key] == {}

    assert "arima" in registry.metadata.future_plugins
    assert "prophet" in registry.metadata.future_plugins
    assert "timesfm" in registry.metadata.future_plugins
    assert "chronos" in registry.metadata.future_plugins
    assert "paper_trading" in registry.metadata.future_extensions
    assert "live_prediction" in registry.metadata.future_extensions
    assert "auto_ml" in registry.metadata.future_extensions


def test_immutability():
    registry = build_plugin_registry()
    snapshot = registry.model_dump()
    found = find_plugin(registry, "statistical_plugin")
    assert found is not None
    found.plugin_name = "mutated"
    listed = list_plugins(registry)
    listed[0].plugin_name = "mutated_list"
    plugins_by_type(registry, PluginType.hybrid)
    plugins_by_domain(registry, "Finance")
    plugins_by_capability(registry, PluginCapability.probabilistic)
    plugin_statistics(registry)
    validate_plugin_registry(registry)
    register_plugin(
        registry,
        ForecastPlugin(
            plugin_id="temp",
            plugin_name="Temp",
            plugin_type=PluginType.custom,
        ),
    )
    unregister_plugin(registry, "statistical_plugin")
    assert registry.model_dump() == snapshot
