from __future__ import annotations

from backend.models.ai_insight_models import utc_now_iso
from backend.models.forecast_adapter_models import (
    FORECAST_ADAPTER_INTERFACE_METHODS,
    FORECAST_ADAPTER_SCHEMA_VERSION,
    AdapterExecutionStatus,
    AdapterStatistics,
    AdapterType,
    ForecastAdapter,
    ForecastAdapterInterfaceSpec,
    ForecastAdapterRegistry,
    AdapterRegistryMetadata,
    empty_forecast_adapter_future_extensions,
    empty_forecast_future_adapters,
)

# Built-in type-level adapter catalog entries. Metadata only — no forecasting logic.
_BUILTIN_ADAPTER_SPECS: tuple[dict[str, object], ...] = (
    {
        "adapter_id": "statistical_adapter",
        "adapter_name": "Statistical Forecast Adapter",
        "adapter_type": AdapterType.statistical,
        "description": "Contract for statistical forecasting engines (e.g. ARIMA family). Not implemented.",
        "supported_domains": ["Sales", "Finance", "Operations"],
        "supported_prediction_types": ["Revenue", "Sales", "Demand", "Financial"],
        "required_inputs": ["time_series", "prediction_horizon"],
        "optional_inputs": ["seasonality", "exogenous_features"],
        "expected_outputs": ["forecast_series", "prediction_collection"],
        "confidence_supported": True,
        "training_supported": False,
        "online_learning_supported": False,
        "validation_supported": True,
        "execution_status": AdapterExecutionStatus.registered,
        "dependencies": [],
    },
    {
        "adapter_id": "machine_learning_adapter",
        "adapter_name": "Machine Learning Forecast Adapter",
        "adapter_type": AdapterType.machine_learning,
        "description": "Contract for classical ML forecasting engines. Not implemented.",
        "supported_domains": ["Sales", "Customer", "Inventory", "Operations"],
        "supported_prediction_types": ["Sales", "Demand", "Inventory", "Customer", "Business KPI"],
        "required_inputs": ["feature_matrix", "target_metric", "prediction_horizon"],
        "optional_inputs": ["hyperparameters", "validation_split"],
        "expected_outputs": ["forecast_series", "feature_importance", "prediction_collection"],
        "confidence_supported": True,
        "training_supported": True,
        "online_learning_supported": False,
        "validation_supported": True,
        "execution_status": AdapterExecutionStatus.registered,
        "dependencies": ["statistical_adapter"],
    },
    {
        "adapter_id": "deep_learning_adapter",
        "adapter_name": "Deep Learning Forecast Adapter",
        "adapter_type": AdapterType.deep_learning,
        "description": "Contract for deep learning forecasting engines. Not implemented.",
        "supported_domains": ["Sales", "Demand", "Operations", "Finance"],
        "supported_prediction_types": ["Demand", "Revenue", "Operational", "Custom"],
        "required_inputs": ["sequence_tensor", "prediction_horizon"],
        "optional_inputs": ["architecture_config", "device"],
        "expected_outputs": ["forecast_series", "prediction_collection"],
        "confidence_supported": True,
        "training_supported": True,
        "online_learning_supported": False,
        "validation_supported": True,
        "execution_status": AdapterExecutionStatus.registered,
        "dependencies": ["machine_learning_adapter"],
    },
    {
        "adapter_id": "llm_forecasting_adapter",
        "adapter_name": "LLM Forecasting Adapter",
        "adapter_type": AdapterType.llm_forecasting,
        "description": "Contract for LLM-assisted forecasting. Not implemented.",
        "supported_domains": ["Business", "Sales", "Risk"],
        "supported_prediction_types": ["Business KPI", "Risk", "Custom"],
        "required_inputs": ["intelligence_bundle", "prediction_context"],
        "optional_inputs": ["prompt_template", "analyst_context"],
        "expected_outputs": ["forecast_narrative", "prediction_collection"],
        "confidence_supported": True,
        "training_supported": False,
        "online_learning_supported": False,
        "validation_supported": True,
        "execution_status": AdapterExecutionStatus.experimental,
        "dependencies": ["rule_based_adapter"],
    },
    {
        "adapter_id": "rule_based_adapter",
        "adapter_name": "Rule Based Forecast Adapter",
        "adapter_type": AdapterType.rule_based,
        "description": "Contract for rule-based / heuristic forecasting. Not implemented.",
        "supported_domains": ["Sales", "Operations", "Inventory"],
        "supported_prediction_types": ["Sales", "Demand", "Inventory", "Operational"],
        "required_inputs": ["decision_collection", "prediction_horizon"],
        "optional_inputs": ["business_rules"],
        "expected_outputs": ["prediction_collection"],
        "confidence_supported": True,
        "training_supported": False,
        "online_learning_supported": False,
        "validation_supported": True,
        "execution_status": AdapterExecutionStatus.available,
        "dependencies": [],
    },
    {
        "adapter_id": "hybrid_adapter",
        "adapter_name": "Hybrid Forecast Adapter",
        "adapter_type": AdapterType.hybrid,
        "description": "Contract for hybrid statistical + ML + rule forecasting. Not implemented.",
        "supported_domains": ["Sales", "Finance", "Operations", "Customer"],
        "supported_prediction_types": [
            "Revenue",
            "Sales",
            "Demand",
            "Financial",
            "Business KPI",
        ],
        "required_inputs": ["time_series", "feature_matrix", "intelligence_bundle"],
        "optional_inputs": ["ensemble_weights"],
        "expected_outputs": ["forecast_series", "prediction_collection", "scenario_set"],
        "confidence_supported": True,
        "training_supported": True,
        "online_learning_supported": True,
        "validation_supported": True,
        "execution_status": AdapterExecutionStatus.registered,
        "dependencies": [
            "statistical_adapter",
            "machine_learning_adapter",
            "rule_based_adapter",
        ],
    },
    {
        "adapter_id": "custom_adapter",
        "adapter_name": "Custom Forecast Adapter",
        "adapter_type": AdapterType.custom,
        "description": "Contract for custom / plugin forecasting engines. Not implemented.",
        "supported_domains": ["Custom"],
        "supported_prediction_types": ["Custom"],
        "required_inputs": ["custom_payload"],
        "optional_inputs": ["plugin_config"],
        "expected_outputs": ["prediction_collection"],
        "confidence_supported": False,
        "training_supported": False,
        "online_learning_supported": False,
        "validation_supported": True,
        "execution_status": AdapterExecutionStatus.registered,
        "dependencies": [],
    },
)


def _as_adapter(spec: dict[str, object]) -> ForecastAdapter:
    status = spec.get("execution_status", AdapterExecutionStatus.registered)
    if isinstance(status, str):
        status = AdapterExecutionStatus(status)
    adapter_type = spec["adapter_type"]
    if isinstance(adapter_type, str):
        adapter_type = AdapterType(adapter_type)
    return ForecastAdapter(
        adapter_id=str(spec["adapter_id"]),
        adapter_name=str(spec["adapter_name"]),
        adapter_type=adapter_type,  # type: ignore[arg-type]
        version=str(spec.get("version", FORECAST_ADAPTER_SCHEMA_VERSION)),
        description=str(spec.get("description", "")),
        supported_domains=list(spec.get("supported_domains", [])),  # type: ignore[arg-type]
        supported_prediction_types=list(spec.get("supported_prediction_types", [])),  # type: ignore[arg-type]
        required_inputs=list(spec.get("required_inputs", [])),  # type: ignore[arg-type]
        optional_inputs=list(spec.get("optional_inputs", [])),  # type: ignore[arg-type]
        expected_outputs=list(spec.get("expected_outputs", [])),  # type: ignore[arg-type]
        confidence_supported=bool(spec.get("confidence_supported", False)),
        training_supported=bool(spec.get("training_supported", False)),
        online_learning_supported=bool(spec.get("online_learning_supported", False)),
        validation_supported=bool(spec.get("validation_supported", False)),
        execution_status=status,  # type: ignore[arg-type]
        dependencies=list(spec.get("dependencies", [])),  # type: ignore[arg-type]
        interface=ForecastAdapterInterfaceSpec(),
        metadata=dict(spec.get("metadata", {})),  # type: ignore[arg-type]
    )


def register_adapter(
    registry: ForecastAdapterRegistry,
    adapter: ForecastAdapter,
    *,
    replace: bool = True,
) -> ForecastAdapterRegistry:
    """Register or replace one adapter catalog entry. Does not mutate the input registry."""
    copy = registry.model_copy(deep=True)
    adapters = list(copy.adapters)
    adapter_copy = adapter.model_copy(deep=True)
    if not adapter_copy.interface.methods:
        adapter_copy.interface = ForecastAdapterInterfaceSpec()
    existing_idx = next(
        (i for i, item in enumerate(adapters) if item.adapter_id == adapter_copy.adapter_id),
        None,
    )
    if existing_idx is None:
        adapters.append(adapter_copy)
    elif replace:
        adapters[existing_idx] = adapter_copy
    else:
        return copy
    copy.adapters = adapters
    return copy


def find_adapter(registry: ForecastAdapterRegistry, adapter_id: str) -> ForecastAdapter | None:
    for adapter in registry.adapters:
        if adapter.adapter_id == adapter_id:
            return adapter.model_copy(deep=True)
    return None


def list_adapters(
    registry: ForecastAdapterRegistry,
    *,
    execution_status: AdapterExecutionStatus | str | None = None,
) -> list[ForecastAdapter]:
    status_value = (
        execution_status.value
        if isinstance(execution_status, AdapterExecutionStatus)
        else execution_status
    )
    results: list[ForecastAdapter] = []
    for adapter in registry.adapters:
        if status_value is not None and adapter.execution_status.value != status_value:
            continue
        results.append(adapter.model_copy(deep=True))
    return results


def adapters_by_type(
    registry: ForecastAdapterRegistry,
    adapter_type: AdapterType | str,
) -> list[ForecastAdapter]:
    type_value = adapter_type.value if isinstance(adapter_type, AdapterType) else adapter_type
    return [
        adapter.model_copy(deep=True)
        for adapter in registry.adapters
        if adapter.adapter_type.value == type_value
    ]


def adapters_by_domain(
    registry: ForecastAdapterRegistry,
    domain: str,
) -> list[ForecastAdapter]:
    needle = domain.strip().lower()
    return [
        adapter.model_copy(deep=True)
        for adapter in registry.adapters
        if any(item.lower() == needle for item in adapter.supported_domains)
    ]


def validate_adapter(adapter: ForecastAdapter) -> dict[str, object]:
    """Structural integrity for one adapter — never executes forecasting."""
    issues: list[str] = []
    if not adapter.adapter_id:
        issues.append("Missing adapter_id")
    if not adapter.adapter_name:
        issues.append("Missing adapter_name")
    if adapter.adapter_type not in AdapterType:
        issues.append(f"Unsupported adapter_type: {adapter.adapter_type}")
    if not adapter.version:
        issues.append("Missing version")
    missing_methods = [
        method
        for method in FORECAST_ADAPTER_INTERFACE_METHODS
        if method not in adapter.interface.methods
    ]
    if missing_methods:
        issues.append(f"Missing interface methods: {', '.join(missing_methods)}")
    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "adapter_id": adapter.adapter_id,
    }


def validate_adapter_registry(registry: ForecastAdapterRegistry) -> dict[str, object]:
    """Structural integrity for the adapter registry."""
    issues: list[str] = []
    seen: set[str] = set()
    adapter_ids = {adapter.adapter_id for adapter in registry.adapters}

    for adapter in registry.adapters:
        result = validate_adapter(adapter)
        issues.extend(str(item) for item in result["issues"])  # type: ignore[index]
        if adapter.adapter_id in seen:
            issues.append(f"Duplicate adapter_id: {adapter.adapter_id}")
        seen.add(adapter.adapter_id)
        for dep in adapter.dependencies:
            if dep not in adapter_ids:
                issues.append(f"Missing dependency adapter: {adapter.adapter_id} -> {dep}")

    contract_methods = set(registry.interface_contract.methods)
    required = set(FORECAST_ADAPTER_INTERFACE_METHODS)
    if not required.issubset(contract_methods):
        issues.append(
            f"Registry interface missing methods: {', '.join(sorted(required - contract_methods))}"
        )

    required_extensions = set(empty_forecast_adapter_future_extensions().keys())
    missing_extensions = sorted(
        required_extensions - set(registry.metadata.future_extensions.keys())
    )
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    required_adapters = set(empty_forecast_future_adapters().keys())
    missing_adapters = sorted(required_adapters - set(registry.metadata.future_adapters.keys()))
    if missing_adapters:
        issues.append(f"Missing future_adapters: {', '.join(missing_adapters)}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "registry_id": registry.registry_id,
        "adapter_count": len(registry.adapters),
    }


def adapter_statistics(registry: ForecastAdapterRegistry) -> AdapterStatistics:
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    confidence = training = validation = online = 0

    for adapter in registry.adapters:
        by_type[adapter.adapter_type.value] = by_type.get(adapter.adapter_type.value, 0) + 1
        by_status[adapter.execution_status.value] = (
            by_status.get(adapter.execution_status.value, 0) + 1
        )
        for domain in adapter.supported_domains:
            by_domain[domain] = by_domain.get(domain, 0) + 1
        if adapter.confidence_supported:
            confidence += 1
        if adapter.training_supported:
            training += 1
        if adapter.validation_supported:
            validation += 1
        if adapter.online_learning_supported:
            online += 1

    return AdapterStatistics(
        total_adapters=len(registry.adapters),
        by_type=by_type,
        by_status=by_status,
        by_domain=by_domain,
        confidence_supported_count=confidence,
        training_supported_count=training,
        validation_supported_count=validation,
        online_learning_supported_count=online,
    )


def build_adapter_registry(*, include_builtins: bool = True) -> ForecastAdapterRegistry:
    """Build the read-only forecast adapter catalog. Architecture only — no execution."""
    now = utc_now_iso()
    adapters: list[ForecastAdapter] = []
    if include_builtins:
        adapters = [_as_adapter(spec) for spec in _BUILTIN_ADAPTER_SPECS]

    return ForecastAdapterRegistry(
        registry_id=f"forecast_adapter_registry_{now.replace(':', '').replace('-', '')}",
        schema_version=FORECAST_ADAPTER_SCHEMA_VERSION,
        adapters=adapters,
        interface_contract=ForecastAdapterInterfaceSpec(),
        generated_at=now,
        metadata=AdapterRegistryMetadata(
            legacy={"schema": FORECAST_ADAPTER_SCHEMA_VERSION},
            debug={
                "adapter_count": len(adapters),
                "types_present": sorted({a.adapter_type.value for a in adapters}),
            },
            custom={},
            future_extensions=empty_forecast_adapter_future_extensions(),
            future_adapters=empty_forecast_future_adapters(),
        ),
    )
