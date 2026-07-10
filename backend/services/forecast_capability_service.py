from __future__ import annotations

from backend.models.ai_insight_models import utc_now_iso
from backend.models.forecast_capability_models import (
    FORECAST_CAPABILITY_SCHEMA_VERSION,
    CapabilityRegistryMetadata,
    CapabilityRegistrySummary,
    CapabilityStatistics,
    CapabilityStatus,
    CapabilityType,
    ForecastCapability,
    ForecastCapabilityRegistry,
    empty_forecast_capability_future_extensions,
)

# Built-in capability catalog. Metadata only — no forecasting execution.
_BUILTIN_CAPABILITY_SPECS: tuple[dict[str, object], ...] = (
    {
        "capability_id": "forecast_adapter_framework",
        "capability_name": "Forecast Adapter Framework",
        "capability_type": CapabilityType.adapter,
        "status": CapabilityStatus.available,
        "supported_data_types": ["tabular", "time_series"],
        "supported_time_granularity": ["D", "W", "M"],
        "supported_targets": ["revenue", "sales", "demand"],
        "supported_features": ["adapter_contract", "interface_spec"],
        "required_inputs": ["adapter_registry"],
        "optional_inputs": ["domain"],
        "produced_outputs": ["adapter_catalog"],
        "dependencies": [],
        "limitations": ["Does not execute forecasting adapters."],
        "owner": "platform",
    },
    {
        "capability_id": "forecast_pipeline",
        "capability_name": "Forecast Pipeline",
        "capability_type": CapabilityType.pipeline,
        "status": CapabilityStatus.available,
        "supported_data_types": ["tabular", "time_series"],
        "supported_time_granularity": ["D", "W", "M", "Q"],
        "supported_targets": ["revenue", "sales", "demand", "kpi"],
        "supported_features": ["stage_graph", "pipeline_metadata"],
        "required_inputs": ["dataset_id"],
        "optional_inputs": ["adapter_id", "execution_mode"],
        "produced_outputs": ["pipeline_metadata"],
        "dependencies": ["forecast_adapter_framework"],
        "limitations": ["Orchestration metadata only; no pipeline execution."],
        "owner": "platform",
    },
    {
        "capability_id": "prediction_engine",
        "capability_name": "Prediction Engine",
        "capability_type": CapabilityType.prediction,
        "status": CapabilityStatus.available,
        "supported_data_types": ["intelligence_objects"],
        "supported_time_granularity": ["ShortTerm", "MediumTerm", "LongTerm"],
        "supported_targets": ["revenue", "sales", "risk", "kpi"],
        "supported_features": ["structured_prediction", "scenarios"],
        "required_inputs": ["insight_or_decision"],
        "optional_inputs": ["bundle", "registry", "analyst_context"],
        "produced_outputs": ["prediction_collection"],
        "dependencies": [],
        "limitations": ["No ML training; consumes existing intelligence only."],
        "owner": "platform",
    },
    {
        "capability_id": "prediction_validation",
        "capability_name": "Prediction Validation",
        "capability_type": CapabilityType.validation,
        "status": CapabilityStatus.available,
        "supported_data_types": ["prediction_collection", "observed_results"],
        "supported_time_granularity": ["any"],
        "supported_targets": ["prediction_quality"],
        "supported_features": ["accuracy_metrics", "learning_records"],
        "required_inputs": ["prediction_collection"],
        "optional_inputs": ["observed_results", "bundle", "registry"],
        "produced_outputs": ["prediction_validation_collection"],
        "dependencies": ["prediction_engine"],
        "limitations": ["Does not retrain models; observed values must be supplied."],
        "owner": "platform",
    },
    {
        "capability_id": "future_statistical_forecast",
        "capability_name": "Future Statistical Forecast",
        "capability_type": CapabilityType.statistical,
        "status": CapabilityStatus.planned,
        "supported_data_types": ["time_series"],
        "supported_time_granularity": ["D", "W", "M"],
        "supported_targets": ["revenue", "sales", "demand"],
        "supported_features": ["seasonality", "trend"],
        "required_inputs": ["time_series", "horizon"],
        "optional_inputs": ["exogenous_features"],
        "produced_outputs": ["forecast_series", "prediction_collection"],
        "dependencies": ["forecast_adapter_framework", "forecast_pipeline", "prediction_engine"],
        "limitations": ["Not implemented. Placeholder capability only."],
        "owner": "platform",
    },
    {
        "capability_id": "future_machine_learning_forecast",
        "capability_name": "Future Machine Learning Forecast",
        "capability_type": CapabilityType.machine_learning,
        "status": CapabilityStatus.planned,
        "supported_data_types": ["tabular", "time_series"],
        "supported_time_granularity": ["D", "W", "M"],
        "supported_targets": ["sales", "demand", "inventory", "customer"],
        "supported_features": ["lag", "rolling", "categorical"],
        "required_inputs": ["feature_matrix", "target", "horizon"],
        "optional_inputs": ["hyperparameters"],
        "produced_outputs": ["forecast_series", "prediction_collection"],
        "dependencies": [
            "forecast_adapter_framework",
            "forecast_pipeline",
            "prediction_engine",
            "prediction_validation",
        ],
        "limitations": ["Not implemented. Placeholder capability only."],
        "owner": "platform",
    },
    {
        "capability_id": "future_deep_learning_forecast",
        "capability_name": "Future Deep Learning Forecast",
        "capability_type": CapabilityType.deep_learning,
        "status": CapabilityStatus.experimental,
        "supported_data_types": ["sequence", "time_series"],
        "supported_time_granularity": ["H", "D", "W"],
        "supported_targets": ["demand", "revenue"],
        "supported_features": ["sequence", "embedding"],
        "required_inputs": ["sequence_tensor", "horizon"],
        "optional_inputs": ["architecture_config"],
        "produced_outputs": ["forecast_series", "prediction_collection"],
        "dependencies": [
            "forecast_adapter_framework",
            "forecast_pipeline",
            "future_machine_learning_forecast",
        ],
        "limitations": ["Not implemented. Placeholder capability only."],
        "owner": "platform",
    },
    {
        "capability_id": "future_ensemble_forecast",
        "capability_name": "Future Ensemble Forecast",
        "capability_type": CapabilityType.ensemble,
        "status": CapabilityStatus.planned,
        "supported_data_types": ["time_series", "tabular"],
        "supported_time_granularity": ["D", "W", "M", "Q"],
        "supported_targets": ["revenue", "sales", "demand", "kpi"],
        "supported_features": ["ensemble_weights", "model_blend"],
        "required_inputs": ["member_forecasts"],
        "optional_inputs": ["weights"],
        "produced_outputs": ["ensemble_forecast", "prediction_collection"],
        "dependencies": [
            "future_statistical_forecast",
            "future_machine_learning_forecast",
            "future_deep_learning_forecast",
            "prediction_validation",
        ],
        "limitations": ["Not implemented. Placeholder capability only."],
        "owner": "platform",
    },
)


def _as_capability(spec: dict[str, object], now: str) -> ForecastCapability:
    status = spec.get("status", CapabilityStatus.planned)
    if isinstance(status, str):
        status = CapabilityStatus(status)
    ctype = spec["capability_type"]
    if isinstance(ctype, str):
        ctype = CapabilityType(ctype)
    return ForecastCapability(
        capability_id=str(spec["capability_id"]),
        capability_name=str(spec["capability_name"]),
        capability_type=ctype,  # type: ignore[arg-type]
        version=str(spec.get("version", FORECAST_CAPABILITY_SCHEMA_VERSION)),
        status=status,  # type: ignore[arg-type]
        supported_data_types=list(spec.get("supported_data_types", [])),  # type: ignore[arg-type]
        supported_time_granularity=list(spec.get("supported_time_granularity", [])),  # type: ignore[arg-type]
        supported_targets=list(spec.get("supported_targets", [])),  # type: ignore[arg-type]
        supported_features=list(spec.get("supported_features", [])),  # type: ignore[arg-type]
        required_inputs=list(spec.get("required_inputs", [])),  # type: ignore[arg-type]
        optional_inputs=list(spec.get("optional_inputs", [])),  # type: ignore[arg-type]
        produced_outputs=list(spec.get("produced_outputs", [])),  # type: ignore[arg-type]
        dependencies=list(spec.get("dependencies", [])),  # type: ignore[arg-type]
        limitations=list(spec.get("limitations", [])),  # type: ignore[arg-type]
        owner=str(spec.get("owner", "platform")),
        created_at=str(spec.get("created_at", now)),
        updated_at=str(spec.get("updated_at", now)),
        metadata=dict(spec.get("metadata", {})),  # type: ignore[arg-type]
    )


def register_capability(
    registry: ForecastCapabilityRegistry,
    capability: ForecastCapability,
    *,
    replace: bool = True,
) -> ForecastCapabilityRegistry:
    """Register or replace one capability. Does not mutate the input registry."""
    copy = registry.model_copy(deep=True)
    capabilities = list(copy.capabilities)
    item = capability.model_copy(deep=True)
    if not item.updated_at:
        item.updated_at = utc_now_iso()
    existing_idx = next(
        (i for i, c in enumerate(capabilities) if c.capability_id == item.capability_id),
        None,
    )
    if existing_idx is None:
        capabilities.append(item)
    elif replace:
        capabilities[existing_idx] = item
    else:
        return copy
    copy.capabilities = capabilities
    return copy


def find_capability(
    registry: ForecastCapabilityRegistry,
    capability_id: str,
) -> ForecastCapability | None:
    for item in registry.capabilities:
        if item.capability_id == capability_id:
            return item.model_copy(deep=True)
    return None


def list_capabilities(
    registry: ForecastCapabilityRegistry,
    *,
    status: CapabilityStatus | str | None = None,
    capability_type: CapabilityType | str | None = None,
) -> list[ForecastCapability]:
    status_value = status.value if isinstance(status, CapabilityStatus) else status
    type_value = (
        capability_type.value if isinstance(capability_type, CapabilityType) else capability_type
    )
    results: list[ForecastCapability] = []
    for item in registry.capabilities:
        if status_value is not None and item.status.value != status_value:
            continue
        if type_value is not None and item.capability_type.value != type_value:
            continue
        results.append(item.model_copy(deep=True))
    return results


def find_dependencies(registry: ForecastCapabilityRegistry, capability_id: str) -> list[str]:
    for item in registry.capabilities:
        if item.capability_id == capability_id:
            return list(item.dependencies)
    return []


def find_dependents(registry: ForecastCapabilityRegistry, capability_id: str) -> list[str]:
    return [
        item.capability_id
        for item in registry.capabilities
        if capability_id in item.dependencies
    ]


def _detect_cycles(capabilities: list[ForecastCapability]) -> list[list[str]]:
    graph = {item.capability_id: list(item.dependencies) for item in capabilities}
    cycles: list[list[str]] = []
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            if node in stack:
                idx = stack.index(node)
                cycles.append(stack[idx:] + [node])
            return
        visiting.add(node)
        stack.append(node)
        for dep in graph.get(node, []):
            if dep in graph:
                dfs(dep)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        dfs(node)
    return cycles


def registry_statistics(registry: ForecastCapabilityRegistry) -> CapabilityStatistics:
    by_type: dict[str, int] = {}
    active = planned = experimental = deprecated = disabled = 0
    dependency_count = 0

    for item in registry.capabilities:
        by_type[item.capability_type.value] = by_type.get(item.capability_type.value, 0) + 1
        dependency_count += len(item.dependencies)
        if item.status == CapabilityStatus.available:
            active += 1
        elif item.status == CapabilityStatus.planned:
            planned += 1
        elif item.status == CapabilityStatus.experimental:
            experimental += 1
        elif item.status == CapabilityStatus.deprecated:
            deprecated += 1
        elif item.status == CapabilityStatus.disabled:
            disabled += 1

    return CapabilityStatistics(
        total_capabilities=len(registry.capabilities),
        active_capabilities=active,
        planned_capabilities=planned,
        experimental_capabilities=experimental,
        deprecated_capabilities=deprecated,
        disabled_capabilities=disabled,
        capability_type_breakdown=by_type,
        dependency_count=dependency_count,
    )


def registry_summary(registry: ForecastCapabilityRegistry) -> CapabilityRegistrySummary:
    stats = registry_statistics(registry)
    if stats.total_capabilities == 0:
        health = "empty"
    elif stats.active_capabilities > 0 and stats.planned_capabilities >= 0:
        health = "healthy"
    else:
        health = "degraded"
    return CapabilityRegistrySummary(
        registry_version=registry.schema_version,
        total_capabilities=stats.total_capabilities,
        available=stats.active_capabilities,
        planned=stats.planned_capabilities,
        experimental=stats.experimental_capabilities,
        dependency_count=stats.dependency_count,
        overall_health=health,
    )


def validate_registry(registry: ForecastCapabilityRegistry) -> dict[str, object]:
    """Structural integrity only — never executes capabilities."""
    issues: list[str] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    capability_ids = {item.capability_id for item in registry.capabilities}

    if not registry.capabilities:
        issues.append("Empty registry")

    for item in registry.capabilities:
        if not item.capability_id:
            issues.append("Capability missing capability_id")
            continue
        if item.capability_id in seen_ids:
            issues.append(f"Duplicate capability_id: {item.capability_id}")
        seen_ids.add(item.capability_id)

        name_key = item.capability_name.strip().lower()
        if name_key in seen_names:
            issues.append(f"Duplicate capability_name: {item.capability_name}")
        seen_names.add(name_key)

        if item.status not in CapabilityStatus:
            issues.append(f"Invalid status: {item.capability_id}")
        if item.capability_type not in CapabilityType:
            issues.append(f"Invalid capability_type: {item.capability_id}")

        for dep in item.dependencies:
            if dep not in capability_ids:
                issues.append(f"Missing dependency: {item.capability_id} -> {dep}")

    # Orphans: planned/experimental future caps with no dependents and no deps are OK;
    # orphan = has no dependencies AND nothing depends on it AND type is not a root platform type.
    root_types = {
        CapabilityType.adapter,
        CapabilityType.pipeline,
        CapabilityType.prediction,
        CapabilityType.validation,
    }
    for item in registry.capabilities:
        if item.capability_type in root_types:
            continue
        if item.dependencies:
            continue
        if not find_dependents(registry, item.capability_id):
            issues.append(f"Orphan capability: {item.capability_id}")

    for cycle in _detect_cycles(registry.capabilities):
        issues.append(f"Circular dependency: {' -> '.join(cycle)}")

    required_extensions = set(empty_forecast_capability_future_extensions().keys())
    missing_extensions = sorted(
        required_extensions - set(registry.metadata.future_extensions.keys())
    )
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "registry_id": registry.registry_id,
        "capability_count": len(registry.capabilities),
        "circular_dependencies": _detect_cycles(registry.capabilities),
    }


def build_capability_registry(*, include_builtins: bool = True) -> ForecastCapabilityRegistry:
    """Build the read-only forecast capability catalog. Metadata only."""
    now = utc_now_iso()
    capabilities: list[ForecastCapability] = []
    if include_builtins:
        capabilities = [_as_capability(spec, now) for spec in _BUILTIN_CAPABILITY_SPECS]

    return ForecastCapabilityRegistry(
        registry_id=f"forecast_capability_registry_{now.replace(':', '').replace('-', '')}",
        schema_version=FORECAST_CAPABILITY_SCHEMA_VERSION,
        capabilities=capabilities,
        generated_at=now,
        metadata=CapabilityRegistryMetadata(
            legacy={"schema": FORECAST_CAPABILITY_SCHEMA_VERSION},
            debug={
                "capability_count": len(capabilities),
                "types_present": sorted({c.capability_type.value for c in capabilities}),
            },
            custom={},
            future_extensions=empty_forecast_capability_future_extensions(),
        ),
    )
