from __future__ import annotations

from backend.models.ai_insight_models import utc_now_iso
from backend.models.forecast_scenario_models import (
    FORECAST_SCENARIO_SCHEMA_VERSION,
    ForecastScenario,
    ForecastScenarioRegistry,
    ScenarioRegistryMetadata,
    ScenarioRegistrySummary,
    ScenarioStatistics,
    ScenarioStatus,
    ScenarioType,
    empty_forecast_scenario_future_extensions,
)

# Built-in scenario catalog. Metadata only — no simulation or forecasting.
_BUILTIN_SCENARIO_SPECS: tuple[dict[str, object], ...] = (
    {
        "scenario_id": "baseline",
        "scenario_name": "Baseline",
        "scenario_type": ScenarioType.baseline,
        "description": "Baseline forecast scenario using current validated intelligence assumptions.",
        "status": ScenarioStatus.available,
        "priority": 10,
        "applicable_domains": ["Sales", "Finance", "Operations"],
        "supported_targets": ["revenue", "sales", "demand", "kpi"],
        "supported_granularity": ["daily", "weekly", "monthly"],
        "assumptions": [
            "Current business conditions continue without major shocks.",
            "Existing intelligence confidence bounds remain applicable.",
        ],
        "limitations": [
            "Does not simulate outcomes.",
            "No Monte Carlo or statistical sampling.",
        ],
        "dependencies": [],
    },
    {
        "scenario_id": "expected",
        "scenario_name": "Expected",
        "scenario_type": ScenarioType.expected,
        "description": "Expected scenario aligned to the most likely validated outlook.",
        "status": ScenarioStatus.available,
        "priority": 20,
        "applicable_domains": ["Sales", "Finance", "Operations", "Business"],
        "supported_targets": ["revenue", "sales", "demand", "kpi"],
        "supported_granularity": ["daily", "weekly", "monthly", "quarterly"],
        "assumptions": [
            "Expected path follows baseline intelligence with moderate confidence.",
        ],
        "limitations": [
            "Metadata catalog only; no expected-value calculation.",
        ],
        "dependencies": ["baseline"],
    },
    {
        "scenario_id": "optimistic",
        "scenario_name": "Optimistic",
        "scenario_type": ScenarioType.optimistic,
        "description": "Optimistic scenario metadata for upside planning.",
        "status": ScenarioStatus.available,
        "priority": 30,
        "applicable_domains": ["Sales", "Finance", "Business"],
        "supported_targets": ["revenue", "sales", "demand"],
        "supported_granularity": ["weekly", "monthly", "quarterly"],
        "assumptions": [
            "Favorable conditions relative to baseline.",
            "Uses existing confidence ceiling metadata only.",
        ],
        "limitations": [
            "Does not compute optimistic forecasts.",
        ],
        "dependencies": ["baseline", "expected"],
    },
    {
        "scenario_id": "pessimistic",
        "scenario_name": "Pessimistic",
        "scenario_type": ScenarioType.pessimistic,
        "description": "Pessimistic scenario metadata for downside planning.",
        "status": ScenarioStatus.available,
        "priority": 40,
        "applicable_domains": ["Sales", "Finance", "Risk", "Operations"],
        "supported_targets": ["revenue", "sales", "demand", "risk"],
        "supported_granularity": ["weekly", "monthly", "quarterly"],
        "assumptions": [
            "Adverse conditions relative to baseline.",
            "Uses existing confidence floor metadata only.",
        ],
        "limitations": [
            "Does not compute pessimistic forecasts.",
        ],
        "dependencies": ["baseline", "expected"],
    },
    {
        "scenario_id": "best_case",
        "scenario_name": "Best Case",
        "scenario_type": ScenarioType.best_case,
        "description": "Best-case scenario metadata for upper-bound planning.",
        "status": ScenarioStatus.planned,
        "priority": 50,
        "applicable_domains": ["Sales", "Business"],
        "supported_targets": ["revenue", "sales", "kpi"],
        "supported_granularity": ["monthly", "quarterly"],
        "assumptions": [
            "Maximum favorable conditions within declared planning bounds.",
        ],
        "limitations": [
            "Not simulated. Placeholder for future scenario engines.",
        ],
        "dependencies": ["optimistic"],
    },
    {
        "scenario_id": "worst_case",
        "scenario_name": "Worst Case",
        "scenario_type": ScenarioType.worst_case,
        "description": "Worst-case scenario metadata for lower-bound planning.",
        "status": ScenarioStatus.planned,
        "priority": 60,
        "applicable_domains": ["Finance", "Risk", "Operations"],
        "supported_targets": ["revenue", "risk", "demand"],
        "supported_granularity": ["monthly", "quarterly"],
        "assumptions": [
            "Maximum adverse conditions within declared planning bounds.",
        ],
        "limitations": [
            "Not simulated. Placeholder for future scenario engines.",
        ],
        "dependencies": ["pessimistic"],
    },
    {
        "scenario_id": "custom",
        "scenario_name": "Custom",
        "scenario_type": ScenarioType.custom,
        "description": "Custom scenario slot for user-defined forecast scenario metadata.",
        "status": ScenarioStatus.experimental,
        "priority": 100,
        "applicable_domains": ["Custom"],
        "supported_targets": ["custom"],
        "supported_granularity": ["custom"],
        "assumptions": [
            "Caller supplies custom assumptions via metadata.",
        ],
        "limitations": [
            "No execution. Custom scenario payloads are not evaluated here.",
        ],
        "dependencies": ["baseline"],
    },
)


def _as_scenario(spec: dict[str, object], now: str) -> ForecastScenario:
    status = spec.get("status", ScenarioStatus.planned)
    if isinstance(status, str):
        status = ScenarioStatus(status)
    stype = spec["scenario_type"]
    if isinstance(stype, str):
        stype = ScenarioType(stype)
    return ForecastScenario(
        scenario_id=str(spec["scenario_id"]),
        scenario_name=str(spec["scenario_name"]),
        scenario_type=stype,  # type: ignore[arg-type]
        description=str(spec.get("description", "")),
        status=status,  # type: ignore[arg-type]
        priority=int(spec.get("priority", 0)),
        dataset_id=spec.get("dataset_id"),  # type: ignore[arg-type]
        applicable_domains=list(spec.get("applicable_domains", [])),  # type: ignore[arg-type]
        supported_targets=list(spec.get("supported_targets", [])),  # type: ignore[arg-type]
        supported_granularity=list(spec.get("supported_granularity", [])),  # type: ignore[arg-type]
        assumptions=list(spec.get("assumptions", [])),  # type: ignore[arg-type]
        limitations=list(spec.get("limitations", [])),  # type: ignore[arg-type]
        dependencies=list(spec.get("dependencies", [])),  # type: ignore[arg-type]
        created_at=str(spec.get("created_at", now)),
        updated_at=str(spec.get("updated_at", now)),
        metadata=dict(spec.get("metadata", {})),  # type: ignore[arg-type]
    )


def register_scenario(
    registry: ForecastScenarioRegistry,
    scenario: ForecastScenario,
    *,
    replace: bool = True,
) -> ForecastScenarioRegistry:
    """Register or replace one scenario. Does not mutate the input registry."""
    copy = registry.model_copy(deep=True)
    scenarios = list(copy.scenarios)
    item = scenario.model_copy(deep=True)
    if not item.updated_at:
        item.updated_at = utc_now_iso()
    existing_idx = next(
        (i for i, s in enumerate(scenarios) if s.scenario_id == item.scenario_id),
        None,
    )
    if existing_idx is None:
        scenarios.append(item)
    elif replace:
        scenarios[existing_idx] = item
    else:
        return copy
    copy.scenarios = scenarios
    return copy


def find_scenario(
    registry: ForecastScenarioRegistry,
    scenario_id: str,
) -> ForecastScenario | None:
    for item in registry.scenarios:
        if item.scenario_id == scenario_id:
            return item.model_copy(deep=True)
    return None


def list_scenarios(
    registry: ForecastScenarioRegistry,
    *,
    status: ScenarioStatus | str | None = None,
    scenario_type: ScenarioType | str | None = None,
) -> list[ForecastScenario]:
    status_value = status.value if isinstance(status, ScenarioStatus) else status
    type_value = scenario_type.value if isinstance(scenario_type, ScenarioType) else scenario_type
    results: list[ForecastScenario] = []
    for item in registry.scenarios:
        if status_value is not None and item.status.value != status_value:
            continue
        if type_value is not None and item.scenario_type.value != type_value:
            continue
        results.append(item.model_copy(deep=True))
    return results


def find_dependencies(registry: ForecastScenarioRegistry, scenario_id: str) -> list[str]:
    for item in registry.scenarios:
        if item.scenario_id == scenario_id:
            return list(item.dependencies)
    return []


def find_dependents(registry: ForecastScenarioRegistry, scenario_id: str) -> list[str]:
    return [
        item.scenario_id
        for item in registry.scenarios
        if scenario_id in item.dependencies
    ]


def _detect_cycles(scenarios: list[ForecastScenario]) -> list[list[str]]:
    graph = {item.scenario_id: list(item.dependencies) for item in scenarios}
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


def scenario_statistics(registry: ForecastScenarioRegistry) -> ScenarioStatistics:
    available = planned = experimental = deprecated = disabled = custom = 0
    dependency_count = 0
    for item in registry.scenarios:
        dependency_count += len(item.dependencies)
        if item.scenario_type == ScenarioType.custom:
            custom += 1
        if item.status == ScenarioStatus.available:
            available += 1
        elif item.status == ScenarioStatus.planned:
            planned += 1
        elif item.status == ScenarioStatus.experimental:
            experimental += 1
        elif item.status == ScenarioStatus.deprecated:
            deprecated += 1
        elif item.status == ScenarioStatus.disabled:
            disabled += 1
    return ScenarioStatistics(
        total_scenarios=len(registry.scenarios),
        available=available,
        planned=planned,
        experimental=experimental,
        deprecated=deprecated,
        disabled=disabled,
        custom=custom,
        dependency_count=dependency_count,
    )


def scenario_summary(registry: ForecastScenarioRegistry) -> ScenarioRegistrySummary:
    stats = scenario_statistics(registry)
    if stats.total_scenarios == 0:
        health = "empty"
    elif stats.available > 0:
        health = "healthy"
    else:
        health = "degraded"
    return ScenarioRegistrySummary(
        registry_version=registry.schema_version,
        scenario_count=stats.total_scenarios,
        available=stats.available,
        experimental=stats.experimental,
        dependency_count=stats.dependency_count,
        overall_health=health,
    )


def validate_registry(registry: ForecastScenarioRegistry) -> dict[str, object]:
    """Structural integrity only — never executes or simulates scenarios."""
    issues: list[str] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    scenario_ids = {item.scenario_id for item in registry.scenarios}

    if not registry.scenarios:
        issues.append("Empty registry")

    for item in registry.scenarios:
        if not item.scenario_id:
            issues.append("Scenario missing scenario_id")
            continue
        if item.scenario_id in seen_ids:
            issues.append(f"Duplicate scenario_id: {item.scenario_id}")
        seen_ids.add(item.scenario_id)

        name_key = item.scenario_name.strip().lower()
        if name_key in seen_names:
            issues.append(f"Duplicate scenario_name: {item.scenario_name}")
        seen_names.add(name_key)

        if item.status not in ScenarioStatus:
            issues.append(f"Invalid status: {item.scenario_id}")
        if item.scenario_type not in ScenarioType:
            issues.append(f"Invalid type: {item.scenario_id}")
        if not item.assumptions:
            issues.append(f"Missing assumptions: {item.scenario_id}")
        if not item.limitations:
            issues.append(f"Missing limitations: {item.scenario_id}")

        for dep in item.dependencies:
            if dep not in scenario_ids:
                issues.append(f"Broken dependency: {item.scenario_id} -> {dep}")

    for cycle in _detect_cycles(registry.scenarios):
        issues.append(f"Circular dependency: {' -> '.join(cycle)}")

    required_extensions = set(empty_forecast_scenario_future_extensions().keys())
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
        "scenario_count": len(registry.scenarios),
        "circular_dependencies": _detect_cycles(registry.scenarios),
    }


def build_scenario_registry(*, include_builtins: bool = True) -> ForecastScenarioRegistry:
    """Build the read-only forecast scenario catalog. Metadata only."""
    now = utc_now_iso()
    scenarios: list[ForecastScenario] = []
    if include_builtins:
        scenarios = [_as_scenario(spec, now) for spec in _BUILTIN_SCENARIO_SPECS]

    return ForecastScenarioRegistry(
        registry_id=f"forecast_scenario_registry_{now.replace(':', '').replace('-', '')}",
        schema_version=FORECAST_SCENARIO_SCHEMA_VERSION,
        scenarios=scenarios,
        generated_at=now,
        metadata=ScenarioRegistryMetadata(
            legacy={"schema": FORECAST_SCENARIO_SCHEMA_VERSION},
            debug={
                "scenario_count": len(scenarios),
                "types_present": sorted({s.scenario_type.value for s in scenarios}),
            },
            custom={},
            future_extensions=empty_forecast_scenario_future_extensions(),
        ),
    )
