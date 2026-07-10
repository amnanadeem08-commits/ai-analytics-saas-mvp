from __future__ import annotations

from backend.models.ai_insight_models import utc_now_iso
from backend.models.forecast_plugin_models import (
    FORECAST_PLUGIN_INTERFACE_METHODS,
    FORECAST_PLUGIN_SCHEMA_VERSION,
    ForecastPlugin,
    ForecastPluginInterfaceSpec,
    ForecastPluginRegistry,
    PluginCapability,
    PluginCompatibility,
    PluginExecutionState,
    PluginRegistryMetadata,
    PluginStatistics,
    PluginType,
    empty_forecast_future_plugins,
    empty_forecast_plugin_future_extensions,
)

# Built-in type-level plug-in catalog entries. Metadata only — no forecasting logic.
_BUILTIN_PLUGIN_SPECS: tuple[dict[str, object], ...] = (
    {
        "plugin_id": "statistical_plugin",
        "plugin_name": "Statistical Forecast Plugin",
        "plugin_type": PluginType.statistical,
        "description": "Base plug-in contract for statistical engines. Not implemented.",
        "author": "platform",
        "supported_domains": ["Sales", "Finance", "Operations"],
        "supported_prediction_types": ["Revenue", "Sales", "Demand", "Financial"],
        "supported_time_horizons": ["ShortTerm", "MediumTerm", "LongTerm"],
        "supported_frequencies": ["D", "W", "M"],
        "supported_features": ["lag", "seasonality"],
        "supported_targets": ["revenue", "sales", "demand"],
        "supports_multivariate": False,
        "supports_probabilistic": True,
        "supports_explainability": True,
        "supports_online_learning": False,
        "execution_state": PluginExecutionState.registered,
        "compatibility": PluginCompatibility(
            compatible_adapter_ids=["statistical_adapter"],
            notes="Compatible with statistical forecast adapter contract.",
        ),
        "dependencies": [],
    },
    {
        "plugin_id": "machine_learning_plugin",
        "plugin_name": "Machine Learning Forecast Plugin",
        "plugin_type": PluginType.machine_learning,
        "description": "Base plug-in contract for classical ML engines. Not implemented.",
        "author": "platform",
        "supported_domains": ["Sales", "Customer", "Inventory", "Operations"],
        "supported_prediction_types": ["Sales", "Demand", "Inventory", "Customer", "Business KPI"],
        "supported_time_horizons": ["ShortTerm", "MediumTerm"],
        "supported_frequencies": ["D", "W", "M"],
        "supported_features": ["lag", "rolling", "categorical"],
        "supported_targets": ["sales", "demand", "churn"],
        "supports_multivariate": True,
        "supports_probabilistic": False,
        "supports_explainability": True,
        "supports_online_learning": False,
        "execution_state": PluginExecutionState.registered,
        "compatibility": PluginCompatibility(
            compatible_adapter_ids=["machine_learning_adapter", "statistical_adapter"],
        ),
        "dependencies": ["statistical_plugin"],
    },
    {
        "plugin_id": "deep_learning_plugin",
        "plugin_name": "Deep Learning Forecast Plugin",
        "plugin_type": PluginType.deep_learning,
        "description": "Base plug-in contract for deep learning engines. Not implemented.",
        "author": "platform",
        "supported_domains": ["Sales", "Demand", "Operations", "Finance"],
        "supported_prediction_types": ["Demand", "Revenue", "Operational", "Custom"],
        "supported_time_horizons": ["ShortTerm", "MediumTerm", "LongTerm"],
        "supported_frequencies": ["H", "D", "W"],
        "supported_features": ["sequence", "embedding"],
        "supported_targets": ["demand", "revenue"],
        "supports_multivariate": True,
        "supports_probabilistic": True,
        "supports_explainability": False,
        "supports_online_learning": False,
        "execution_state": PluginExecutionState.registered,
        "compatibility": PluginCompatibility(
            compatible_adapter_ids=["deep_learning_adapter", "machine_learning_adapter"],
        ),
        "dependencies": ["machine_learning_plugin"],
    },
    {
        "plugin_id": "foundation_model_plugin",
        "plugin_name": "Foundation Model Forecast Plugin",
        "plugin_type": PluginType.foundation_model,
        "description": "Base plug-in contract for foundation / pretrained time-series models. Not implemented.",
        "author": "platform",
        "supported_domains": ["Sales", "Demand", "Finance", "Business"],
        "supported_prediction_types": ["Demand", "Revenue", "Business KPI", "Custom"],
        "supported_time_horizons": ["ShortTerm", "MediumTerm", "LongTerm"],
        "supported_frequencies": ["H", "D", "W", "M"],
        "supported_features": ["context_window", "zero_shot"],
        "supported_targets": ["demand", "revenue", "kpi"],
        "supports_multivariate": True,
        "supports_probabilistic": True,
        "supports_explainability": False,
        "supports_online_learning": False,
        "execution_state": PluginExecutionState.experimental,
        "compatibility": PluginCompatibility(
            compatible_adapter_ids=["deep_learning_adapter", "llm_forecasting_adapter"],
        ),
        "dependencies": ["deep_learning_plugin"],
    },
    {
        "plugin_id": "hybrid_plugin",
        "plugin_name": "Hybrid Forecast Plugin",
        "plugin_type": PluginType.hybrid,
        "description": "Base plug-in contract for hybrid statistical + ML engines. Not implemented.",
        "author": "platform",
        "supported_domains": ["Sales", "Finance", "Operations", "Customer"],
        "supported_prediction_types": ["Revenue", "Sales", "Demand", "Financial", "Business KPI"],
        "supported_time_horizons": ["Immediate", "ShortTerm", "MediumTerm", "LongTerm"],
        "supported_frequencies": ["D", "W", "M", "Q"],
        "supported_features": ["lag", "seasonality", "rolling", "rules"],
        "supported_targets": ["revenue", "sales", "demand"],
        "supports_multivariate": True,
        "supports_probabilistic": True,
        "supports_explainability": True,
        "supports_online_learning": True,
        "execution_state": PluginExecutionState.registered,
        "compatibility": PluginCompatibility(
            compatible_adapter_ids=[
                "hybrid_adapter",
                "statistical_adapter",
                "machine_learning_adapter",
                "rule_based_adapter",
            ],
        ),
        "dependencies": [
            "statistical_plugin",
            "machine_learning_plugin",
        ],
    },
    {
        "plugin_id": "trading_plugin",
        "plugin_name": "Trading Forecast Plugin",
        "plugin_type": PluginType.trading,
        "description": "Base plug-in contract for trading forecast engines. Not implemented.",
        "author": "platform",
        "supported_domains": ["Trading", "Finance"],
        "supported_prediction_types": ["Financial", "Risk", "Custom"],
        "supported_time_horizons": ["Immediate", "ShortTerm"],
        "supported_frequencies": ["T", "H", "D"],
        "supported_features": ["price", "volume", "volatility"],
        "supported_targets": ["price", "return", "risk"],
        "supports_multivariate": True,
        "supports_probabilistic": True,
        "supports_explainability": True,
        "supports_online_learning": True,
        "execution_state": PluginExecutionState.experimental,
        "compatibility": PluginCompatibility(
            compatible_adapter_ids=["custom_adapter", "hybrid_adapter"],
            notes="Trading plug-in reserved for future market engines.",
        ),
        "dependencies": ["hybrid_plugin"],
    },
    {
        "plugin_id": "business_plugin",
        "plugin_name": "Business Forecast Plugin",
        "plugin_type": PluginType.business,
        "description": "Base plug-in contract for business KPI forecast engines. Not implemented.",
        "author": "platform",
        "supported_domains": ["Business", "Sales", "Operations"],
        "supported_prediction_types": ["Business KPI", "Revenue", "Sales", "Operational"],
        "supported_time_horizons": ["ShortTerm", "MediumTerm", "LongTerm"],
        "supported_frequencies": ["W", "M", "Q"],
        "supported_features": ["kpi", "decision_context", "bundle_summary"],
        "supported_targets": ["kpi", "revenue", "sales"],
        "supports_multivariate": False,
        "supports_probabilistic": True,
        "supports_explainability": True,
        "supports_online_learning": False,
        "execution_state": PluginExecutionState.available,
        "compatibility": PluginCompatibility(
            compatible_adapter_ids=["rule_based_adapter", "hybrid_adapter", "custom_adapter"],
        ),
        "dependencies": [],
    },
    {
        "plugin_id": "custom_plugin",
        "plugin_name": "Custom Forecast Plugin",
        "plugin_type": PluginType.custom,
        "description": "Base plug-in contract for custom / third-party engines. Not implemented.",
        "author": "platform",
        "supported_domains": ["Custom"],
        "supported_prediction_types": ["Custom"],
        "supported_time_horizons": ["Unknown", "ShortTerm", "MediumTerm", "LongTerm"],
        "supported_frequencies": ["custom"],
        "supported_features": ["custom"],
        "supported_targets": ["custom"],
        "supports_multivariate": False,
        "supports_probabilistic": False,
        "supports_explainability": False,
        "supports_online_learning": False,
        "execution_state": PluginExecutionState.registered,
        "compatibility": PluginCompatibility(
            compatible_adapter_ids=["custom_adapter"],
        ),
        "dependencies": [],
    },
)


def _as_plugin(spec: dict[str, object]) -> ForecastPlugin:
    state = spec.get("execution_state", PluginExecutionState.registered)
    if isinstance(state, str):
        state = PluginExecutionState(state)
    plugin_type = spec["plugin_type"]
    if isinstance(plugin_type, str):
        plugin_type = PluginType(plugin_type)
    compatibility = spec.get("compatibility", PluginCompatibility())
    if isinstance(compatibility, dict):
        compatibility = PluginCompatibility(**compatibility)
    return ForecastPlugin(
        plugin_id=str(spec["plugin_id"]),
        plugin_name=str(spec["plugin_name"]),
        plugin_type=plugin_type,  # type: ignore[arg-type]
        plugin_version=str(spec.get("plugin_version", FORECAST_PLUGIN_SCHEMA_VERSION)),
        description=str(spec.get("description", "")),
        author=str(spec.get("author", "platform")),
        supported_domains=list(spec.get("supported_domains", [])),  # type: ignore[arg-type]
        supported_prediction_types=list(spec.get("supported_prediction_types", [])),  # type: ignore[arg-type]
        supported_time_horizons=list(spec.get("supported_time_horizons", [])),  # type: ignore[arg-type]
        supported_frequencies=list(spec.get("supported_frequencies", [])),  # type: ignore[arg-type]
        supported_features=list(spec.get("supported_features", [])),  # type: ignore[arg-type]
        supported_targets=list(spec.get("supported_targets", [])),  # type: ignore[arg-type]
        supports_multivariate=bool(spec.get("supports_multivariate", False)),
        supports_probabilistic=bool(spec.get("supports_probabilistic", False)),
        supports_explainability=bool(spec.get("supports_explainability", False)),
        supports_online_learning=bool(spec.get("supports_online_learning", False)),
        execution_state=state,  # type: ignore[arg-type]
        compatibility=compatibility,  # type: ignore[arg-type]
        dependencies=list(spec.get("dependencies", [])),  # type: ignore[arg-type]
        interface=ForecastPluginInterfaceSpec(),
        metadata=dict(spec.get("metadata", {})),  # type: ignore[arg-type]
    )


def register_plugin(
    registry: ForecastPluginRegistry,
    plugin: ForecastPlugin,
    *,
    replace: bool = True,
) -> ForecastPluginRegistry:
    """Register or replace one plug-in catalog entry. Does not mutate the input registry."""
    copy = registry.model_copy(deep=True)
    plugins = list(copy.plugins)
    plugin_copy = plugin.model_copy(deep=True)
    if not plugin_copy.interface.methods:
        plugin_copy.interface = ForecastPluginInterfaceSpec()
    existing_idx = next(
        (i for i, item in enumerate(plugins) if item.plugin_id == plugin_copy.plugin_id),
        None,
    )
    if existing_idx is None:
        plugins.append(plugin_copy)
    elif replace:
        plugins[existing_idx] = plugin_copy
    else:
        return copy
    copy.plugins = plugins
    return copy


def unregister_plugin(
    registry: ForecastPluginRegistry,
    plugin_id: str,
) -> ForecastPluginRegistry:
    """Return a new registry without the given plug-in. Does not mutate the input."""
    copy = registry.model_copy(deep=True)
    copy.plugins = [item for item in copy.plugins if item.plugin_id != plugin_id]
    return copy


def find_plugin(registry: ForecastPluginRegistry, plugin_id: str) -> ForecastPlugin | None:
    for plugin in registry.plugins:
        if plugin.plugin_id == plugin_id:
            return plugin.model_copy(deep=True)
    return None


def list_plugins(
    registry: ForecastPluginRegistry,
    *,
    execution_state: PluginExecutionState | str | None = None,
) -> list[ForecastPlugin]:
    state_value = (
        execution_state.value if isinstance(execution_state, PluginExecutionState) else execution_state
    )
    results: list[ForecastPlugin] = []
    for plugin in registry.plugins:
        if state_value is not None and plugin.execution_state.value != state_value:
            continue
        results.append(plugin.model_copy(deep=True))
    return results


def plugins_by_type(
    registry: ForecastPluginRegistry,
    plugin_type: PluginType | str,
) -> list[ForecastPlugin]:
    type_value = plugin_type.value if isinstance(plugin_type, PluginType) else plugin_type
    return [
        plugin.model_copy(deep=True)
        for plugin in registry.plugins
        if plugin.plugin_type.value == type_value
    ]


def plugins_by_domain(
    registry: ForecastPluginRegistry,
    domain: str,
) -> list[ForecastPlugin]:
    needle = domain.strip().lower()
    return [
        plugin.model_copy(deep=True)
        for plugin in registry.plugins
        if any(item.lower() == needle for item in plugin.supported_domains)
    ]


def plugins_by_capability(
    registry: ForecastPluginRegistry,
    capability: PluginCapability | str,
) -> list[ForecastPlugin]:
    cap = capability.value if isinstance(capability, PluginCapability) else capability
    cap = cap.strip().lower()
    results: list[ForecastPlugin] = []
    for plugin in registry.plugins:
        matched = False
        if cap == PluginCapability.multivariate.value and plugin.supports_multivariate:
            matched = True
        elif cap == PluginCapability.probabilistic.value and plugin.supports_probabilistic:
            matched = True
        elif cap == PluginCapability.explainability.value and plugin.supports_explainability:
            matched = True
        elif cap == PluginCapability.online_learning.value and plugin.supports_online_learning:
            matched = True
        if matched:
            results.append(plugin.model_copy(deep=True))
    return results


def _is_fully_compatible(plugin: ForecastPlugin) -> bool:
    compat = plugin.compatibility
    return all(
        [
            compat.adapter_compatible,
            compat.prediction_compatible,
            compat.validation_compatible,
            compat.registry_compatible,
            compat.bundle_compatible,
        ]
    )


def validate_plugin(plugin: ForecastPlugin) -> dict[str, object]:
    """Structural integrity for one plug-in — never executes forecasting."""
    issues: list[str] = []
    if not plugin.plugin_id:
        issues.append("Missing plugin_id")
    if not plugin.plugin_name:
        issues.append("Missing plugin_name")
    if plugin.plugin_type not in PluginType:
        issues.append(f"Unsupported plugin_type: {plugin.plugin_type}")
    if not plugin.plugin_version:
        issues.append("Missing plugin_version")

    missing_methods = [
        method
        for method in FORECAST_PLUGIN_INTERFACE_METHODS
        if method not in plugin.interface.methods
    ]
    if missing_methods:
        issues.append(f"Missing interface methods: {', '.join(missing_methods)}")

    compat = plugin.compatibility
    for flag_name, flag_value in (
        ("adapter_compatible", compat.adapter_compatible),
        ("prediction_compatible", compat.prediction_compatible),
        ("validation_compatible", compat.validation_compatible),
        ("registry_compatible", compat.registry_compatible),
        ("bundle_compatible", compat.bundle_compatible),
    ):
        if not isinstance(flag_value, bool):
            issues.append(f"Invalid compatibility flag: {flag_name}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "plugin_id": plugin.plugin_id,
        "fully_compatible": _is_fully_compatible(plugin),
    }


def validate_plugin_registry(registry: ForecastPluginRegistry) -> dict[str, object]:
    """Structural integrity for the plug-in registry."""
    issues: list[str] = []
    seen: set[str] = set()
    plugin_ids = {plugin.plugin_id for plugin in registry.plugins}

    for plugin in registry.plugins:
        result = validate_plugin(plugin)
        issues.extend(str(item) for item in result["issues"])  # type: ignore[index]
        if plugin.plugin_id in seen:
            issues.append(f"Duplicate plugin_id: {plugin.plugin_id}")
        seen.add(plugin.plugin_id)
        for dep in plugin.dependencies:
            if dep not in plugin_ids:
                issues.append(f"Missing dependency plugin: {plugin.plugin_id} -> {dep}")

    contract_methods = set(registry.interface_contract.methods)
    required = set(FORECAST_PLUGIN_INTERFACE_METHODS)
    if not required.issubset(contract_methods):
        issues.append(
            f"Registry interface missing methods: {', '.join(sorted(required - contract_methods))}"
        )

    required_extensions = set(empty_forecast_plugin_future_extensions().keys())
    missing_extensions = sorted(
        required_extensions - set(registry.metadata.future_extensions.keys())
    )
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    required_plugins = set(empty_forecast_future_plugins().keys())
    missing_plugins = sorted(required_plugins - set(registry.metadata.future_plugins.keys()))
    if missing_plugins:
        issues.append(f"Missing future_plugins: {', '.join(missing_plugins)}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "registry_id": registry.registry_id,
        "plugin_count": len(registry.plugins),
    }


def plugin_statistics(registry: ForecastPluginRegistry) -> PluginStatistics:
    by_type: dict[str, int] = {}
    by_state: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    multivariate = probabilistic = explainability = online = fully = 0

    for plugin in registry.plugins:
        by_type[plugin.plugin_type.value] = by_type.get(plugin.plugin_type.value, 0) + 1
        by_state[plugin.execution_state.value] = by_state.get(plugin.execution_state.value, 0) + 1
        for domain in plugin.supported_domains:
            by_domain[domain] = by_domain.get(domain, 0) + 1
        if plugin.supports_multivariate:
            multivariate += 1
        if plugin.supports_probabilistic:
            probabilistic += 1
        if plugin.supports_explainability:
            explainability += 1
        if plugin.supports_online_learning:
            online += 1
        if _is_fully_compatible(plugin):
            fully += 1

    return PluginStatistics(
        total_plugins=len(registry.plugins),
        by_type=by_type,
        by_state=by_state,
        by_domain=by_domain,
        multivariate_count=multivariate,
        probabilistic_count=probabilistic,
        explainability_count=explainability,
        online_learning_count=online,
        fully_compatible_count=fully,
    )


def build_plugin_registry(*, include_builtins: bool = True) -> ForecastPluginRegistry:
    """Build the read-only forecast plug-in catalog. Architecture only — no execution."""
    now = utc_now_iso()
    plugins: list[ForecastPlugin] = []
    if include_builtins:
        plugins = [_as_plugin(spec) for spec in _BUILTIN_PLUGIN_SPECS]

    return ForecastPluginRegistry(
        registry_id=f"forecast_plugin_registry_{now.replace(':', '').replace('-', '')}",
        schema_version=FORECAST_PLUGIN_SCHEMA_VERSION,
        plugins=plugins,
        interface_contract=ForecastPluginInterfaceSpec(),
        generated_at=now,
        metadata=PluginRegistryMetadata(
            legacy={"schema": FORECAST_PLUGIN_SCHEMA_VERSION},
            debug={
                "plugin_count": len(plugins),
                "types_present": sorted({p.plugin_type.value for p in plugins}),
            },
            custom={},
            future_extensions=empty_forecast_plugin_future_extensions(),
            future_plugins=empty_forecast_future_plugins(),
        ),
    )
