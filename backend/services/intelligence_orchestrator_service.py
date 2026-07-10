from __future__ import annotations

from typing import Any

from backend.models.ai_insight_models import utc_now_iso
from backend.models.intelligence_orchestrator_models import (
    INTELLIGENCE_ORCHESTRATOR_SCHEMA_VERSION,
    IntelligenceOrchestrator,
    OrchestrationStage,
    OrchestratorMetadata,
    OrchestratorStatistics,
    StageStatus,
    empty_intelligence_orchestrator_future_extensions,
)

# Built-in stage catalog. Declares connectivity only — never runs engines.
_BUILTIN_STAGE_SPECS: tuple[dict[str, object], ...] = (
    {
        "stage_id": "insights",
        "stage_name": "Insights",
        "input_objects": ["dataset", "dataset_profile"],
        "output_objects": ["universal_insight", "insight_collection"],
        "dependencies": [],
        "optional_dependencies": [],
        "produced_assets": ["universal_insight"],
        "consumed_assets": ["dataset"],
        "execution_order": 10,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "validation",
        "stage_name": "Validation",
        "input_objects": ["universal_insight", "insight_collection"],
        "output_objects": ["validated_insight", "validation_result"],
        "dependencies": ["insights"],
        "optional_dependencies": [],
        "produced_assets": ["validated_insight"],
        "consumed_assets": ["universal_insight"],
        "execution_order": 20,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "decision",
        "stage_name": "Decision",
        "input_objects": ["validated_insight"],
        "output_objects": ["decision", "decision_collection"],
        "dependencies": ["validation"],
        "optional_dependencies": [],
        "produced_assets": ["decision"],
        "consumed_assets": ["validated_insight"],
        "execution_order": 30,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "root_cause",
        "stage_name": "Root Cause",
        "input_objects": ["decision", "validated_insight"],
        "output_objects": ["root_cause", "root_cause_collection"],
        "dependencies": ["decision"],
        "optional_dependencies": ["validation"],
        "produced_assets": ["root_cause"],
        "consumed_assets": ["decision", "validated_insight"],
        "execution_order": 40,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "executive_reasoning",
        "stage_name": "Executive Reasoning",
        "input_objects": ["decision", "root_cause", "validated_insight"],
        "output_objects": ["executive_reasoning", "reasoning_collection"],
        "dependencies": ["root_cause"],
        "optional_dependencies": ["decision", "validation"],
        "produced_assets": ["executive_reasoning"],
        "consumed_assets": ["decision", "root_cause"],
        "execution_order": 50,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "storyboard",
        "stage_name": "Storyboard",
        "input_objects": ["executive_reasoning", "decision", "root_cause"],
        "output_objects": ["storyboard", "storyboard_section"],
        "dependencies": ["executive_reasoning"],
        "optional_dependencies": ["decision", "root_cause"],
        "produced_assets": ["storyboard"],
        "consumed_assets": ["executive_reasoning"],
        "execution_order": 60,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "bundle",
        "stage_name": "Bundle",
        "input_objects": [
            "storyboard",
            "executive_reasoning",
            "decision",
            "root_cause",
            "validated_insight",
        ],
        "output_objects": ["intelligence_bundle"],
        "dependencies": ["storyboard"],
        "optional_dependencies": [
            "executive_reasoning",
            "decision",
            "root_cause",
            "validation",
        ],
        "produced_assets": ["intelligence_bundle"],
        "consumed_assets": ["storyboard"],
        "execution_order": 70,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "registry",
        "stage_name": "Registry",
        "input_objects": ["intelligence_bundle"],
        "output_objects": ["intelligence_registry", "registry_entry"],
        "dependencies": ["bundle"],
        "optional_dependencies": [],
        "produced_assets": ["intelligence_registry"],
        "consumed_assets": ["intelligence_bundle"],
        "execution_order": 80,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "ai_analyst",
        "stage_name": "AI Analyst",
        "input_objects": ["intelligence_bundle", "intelligence_registry"],
        "output_objects": ["analyst_response", "analyst_skill_result"],
        "dependencies": ["registry"],
        "optional_dependencies": ["bundle"],
        "produced_assets": ["analyst_response"],
        "consumed_assets": ["intelligence_bundle", "intelligence_registry"],
        "execution_order": 90,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "prediction",
        "stage_name": "Prediction",
        "input_objects": ["decision", "validated_insight", "intelligence_bundle"],
        "output_objects": ["prediction", "prediction_collection"],
        "dependencies": ["ai_analyst"],
        "optional_dependencies": ["bundle", "decision", "validation"],
        "produced_assets": ["prediction_collection"],
        "consumed_assets": ["analyst_response", "intelligence_bundle"],
        "execution_order": 100,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "prediction_validation",
        "stage_name": "Prediction Validation",
        "input_objects": ["prediction_collection", "observed_results"],
        "output_objects": ["prediction_validation", "learning_record"],
        "dependencies": ["prediction"],
        "optional_dependencies": ["bundle", "registry"],
        "produced_assets": ["prediction_validation_collection"],
        "consumed_assets": ["prediction_collection"],
        "execution_order": 110,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "forecast_adapter",
        "stage_name": "Forecast Adapter",
        "input_objects": ["prediction_collection", "prediction_validation"],
        "output_objects": ["forecast_adapter_registry", "adapter_contract"],
        "dependencies": ["prediction_validation"],
        "optional_dependencies": ["prediction"],
        "produced_assets": ["forecast_adapter_catalog"],
        "consumed_assets": ["prediction_collection"],
        "execution_order": 120,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "pipeline",
        "stage_name": "Pipeline",
        "input_objects": ["forecast_adapter_registry", "dataset"],
        "output_objects": ["forecast_pipeline", "pipeline_metadata"],
        "dependencies": ["forecast_adapter"],
        "optional_dependencies": ["prediction_validation"],
        "produced_assets": ["forecast_pipeline"],
        "consumed_assets": ["forecast_adapter_catalog"],
        "execution_order": 130,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "capability_registry",
        "stage_name": "Capability Registry",
        "input_objects": ["forecast_pipeline", "forecast_adapter_registry"],
        "output_objects": ["forecast_capability_registry"],
        "dependencies": ["pipeline"],
        "optional_dependencies": ["forecast_adapter"],
        "produced_assets": ["forecast_capability_registry"],
        "consumed_assets": ["forecast_pipeline"],
        "execution_order": 140,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "dataset_readiness",
        "stage_name": "Dataset Readiness",
        "input_objects": ["dataset", "forecast_capability_registry"],
        "output_objects": ["forecast_dataset_readiness"],
        "dependencies": ["capability_registry"],
        "optional_dependencies": ["pipeline"],
        "produced_assets": ["forecast_dataset_readiness"],
        "consumed_assets": ["dataset", "forecast_capability_registry"],
        "execution_order": 150,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "scenario_registry",
        "stage_name": "Scenario Registry",
        "input_objects": ["forecast_dataset_readiness", "forecast_capability_registry"],
        "output_objects": ["forecast_scenario_registry"],
        "dependencies": ["dataset_readiness"],
        "optional_dependencies": ["capability_registry"],
        "produced_assets": ["forecast_scenario_registry"],
        "consumed_assets": ["forecast_dataset_readiness"],
        "execution_order": 160,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "explainability",
        "stage_name": "Explainability",
        "input_objects": [
            "prediction_collection",
            "forecast_scenario_registry",
            "forecast_adapter_registry",
        ],
        "output_objects": ["forecast_explanation"],
        "dependencies": ["scenario_registry"],
        "optional_dependencies": ["prediction", "forecast_adapter"],
        "produced_assets": ["forecast_explanation"],
        "consumed_assets": ["forecast_scenario_registry", "prediction_collection"],
        "execution_order": 170,
        "enabled": True,
        "status": StageStatus.available,
    },
    {
        "stage_id": "governance",
        "stage_name": "Governance",
        "input_objects": [
            "forecast_explanation",
            "forecast_scenario_registry",
            "forecast_pipeline",
        ],
        "output_objects": ["forecast_governance", "forecast_audit_record"],
        "dependencies": ["explainability"],
        "optional_dependencies": ["scenario_registry", "pipeline"],
        "produced_assets": ["forecast_governance"],
        "consumed_assets": ["forecast_explanation"],
        "execution_order": 180,
        "enabled": True,
        "status": StageStatus.available,
    },
)


def _as_stage(spec: dict[str, object]) -> OrchestrationStage:
    status = spec.get("status", StageStatus.planned)
    if isinstance(status, str):
        status = StageStatus(status)
    return OrchestrationStage(
        stage_id=str(spec["stage_id"]),
        stage_name=str(spec["stage_name"]),
        input_objects=list(spec.get("input_objects", [])),  # type: ignore[arg-type]
        output_objects=list(spec.get("output_objects", [])),  # type: ignore[arg-type]
        dependencies=list(spec.get("dependencies", [])),  # type: ignore[arg-type]
        optional_dependencies=list(spec.get("optional_dependencies", [])),  # type: ignore[arg-type]
        produced_assets=list(spec.get("produced_assets", [])),  # type: ignore[arg-type]
        consumed_assets=list(spec.get("consumed_assets", [])),  # type: ignore[arg-type]
        execution_order=int(spec.get("execution_order", 0)),
        enabled=bool(spec.get("enabled", True)),
        status=status,  # type: ignore[arg-type]
        metadata=dict(spec.get("metadata", {})),  # type: ignore[arg-type]
    )


def register_stage(
    orchestrator: IntelligenceOrchestrator,
    stage: OrchestrationStage,
    *,
    replace: bool = True,
) -> IntelligenceOrchestrator:
    """Register or replace one stage. Does not mutate the input orchestrator."""
    copy = orchestrator.model_copy(deep=True)
    item = stage.model_copy(deep=True)
    stages = list(copy.stages)
    existing_idx = next(
        (i for i, s in enumerate(stages) if s.stage_id == item.stage_id),
        None,
    )
    if existing_idx is None:
        stages.append(item)
    elif replace:
        stages[existing_idx] = item
    else:
        return copy
    copy.stages = stages
    copy.metadata.debug = {
        **copy.metadata.debug,
        "stage_count": len(stages),
    }
    return copy


def find_stage(
    orchestrator: IntelligenceOrchestrator,
    stage_id: str,
) -> OrchestrationStage | None:
    for item in orchestrator.stages:
        if item.stage_id == stage_id:
            return item.model_copy(deep=True)
    return None


def find_dependencies(
    orchestrator: IntelligenceOrchestrator,
    stage_id: str,
    *,
    include_optional: bool = False,
) -> list[str]:
    for item in orchestrator.stages:
        if item.stage_id == stage_id:
            deps = list(item.dependencies)
            if include_optional:
                deps.extend(item.optional_dependencies)
            # Preserve order, drop duplicates.
            seen: set[str] = set()
            result: list[str] = []
            for dep in deps:
                if dep and dep not in seen:
                    seen.add(dep)
                    result.append(dep)
            return result
    return []


def find_dependents(
    orchestrator: IntelligenceOrchestrator,
    stage_id: str,
    *,
    include_optional: bool = False,
) -> list[str]:
    result: list[str] = []
    for item in orchestrator.stages:
        deps = list(item.dependencies)
        if include_optional:
            deps.extend(item.optional_dependencies)
        if stage_id in deps:
            result.append(item.stage_id)
    return result


def execution_order(orchestrator: IntelligenceOrchestrator) -> list[str]:
    """Return stage_ids sorted by declared execution_order. Never runs stages."""
    ordered = sorted(orchestrator.stages, key=lambda s: (s.execution_order, s.stage_id))
    return [item.stage_id for item in ordered]


def execution_graph(orchestrator: IntelligenceOrchestrator) -> dict[str, Any]:
    """Build a read-only dependency graph. Metadata only — no scheduling."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for item in sorted(orchestrator.stages, key=lambda s: s.execution_order):
        nodes.append(
            {
                "stage_id": item.stage_id,
                "stage_name": item.stage_name,
                "execution_order": item.execution_order,
                "enabled": item.enabled,
                "status": item.status.value,
            }
        )
        for dep in item.dependencies:
            edges.append(
                {
                    "from": dep,
                    "to": item.stage_id,
                    "kind": "required",
                }
            )
        for dep in item.optional_dependencies:
            edges.append(
                {
                    "from": dep,
                    "to": item.stage_id,
                    "kind": "optional",
                }
            )
    return {
        "orchestrator_id": orchestrator.orchestrator_id,
        "nodes": nodes,
        "edges": edges,
        "ordered_stage_ids": execution_order(orchestrator),
    }


def _detect_cycles(stages: list[OrchestrationStage]) -> list[list[str]]:
    graph = {item.stage_id: list(item.dependencies) for item in stages}
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


def orchestrator_statistics(
    orchestrator: IntelligenceOrchestrator,
) -> OrchestratorStatistics:
    enabled = disabled = available = planned = experimental = 0
    dependency_count = optional_dependency_count = 0
    max_order = 0
    for item in orchestrator.stages:
        dependency_count += len(item.dependencies)
        optional_dependency_count += len(item.optional_dependencies)
        max_order = max(max_order, item.execution_order)
        if item.enabled:
            enabled += 1
        else:
            disabled += 1
        if item.status == StageStatus.available:
            available += 1
        elif item.status == StageStatus.planned:
            planned += 1
        elif item.status == StageStatus.experimental:
            experimental += 1
    return OrchestratorStatistics(
        total_stages=len(orchestrator.stages),
        enabled_stages=enabled,
        disabled_stages=disabled,
        available_stages=available,
        planned_stages=planned,
        experimental_stages=experimental,
        dependency_count=dependency_count,
        optional_dependency_count=optional_dependency_count,
        max_execution_order=max_order,
    )


def validate_orchestrator(orchestrator: IntelligenceOrchestrator) -> dict[str, object]:
    """Structural integrity only — never executes or schedules stages."""
    issues: list[str] = []
    seen_ids: set[str] = set()
    seen_orders: set[int] = set()
    stage_ids = {item.stage_id for item in orchestrator.stages}

    if not orchestrator.stages:
        issues.append("Empty orchestrator")

    for item in orchestrator.stages:
        if not item.stage_id:
            issues.append("Stage missing stage_id")
            continue
        if item.stage_id in seen_ids:
            issues.append(f"Duplicate stage_id: {item.stage_id}")
        seen_ids.add(item.stage_id)

        if item.execution_order in seen_orders:
            issues.append(f"Duplicate execution_order: {item.execution_order}")
        seen_orders.add(item.execution_order)

        try:
            if item.status not in StageStatus:
                issues.append(f"Invalid status: {item.stage_id}")
        except Exception:
            issues.append(f"Invalid status: {item.stage_id}")

        for dep in item.dependencies:
            if dep not in stage_ids:
                issues.append(f"Missing required dependency: {item.stage_id} -> {dep}")

        for dep in item.optional_dependencies:
            if dep not in stage_ids:
                issues.append(f"Missing optional dependency: {item.stage_id} -> {dep}")

    for cycle in _detect_cycles(orchestrator.stages):
        issues.append(f"Circular dependency: {' -> '.join(cycle)}")

    required_extensions = set(empty_intelligence_orchestrator_future_extensions().keys())
    missing_extensions = sorted(
        required_extensions - set(orchestrator.metadata.future_extensions.keys())
    )
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "orchestrator_id": orchestrator.orchestrator_id,
        "stage_count": len(orchestrator.stages),
        "circular_dependencies": _detect_cycles(orchestrator.stages),
        "missing_required_dependencies": [
            i for i in issues if i.startswith("Missing required dependency:")
        ],
        "missing_optional_dependencies": [
            i for i in issues if i.startswith("Missing optional dependency:")
        ],
    }


def build_orchestrator(*, include_builtins: bool = True) -> IntelligenceOrchestrator:
    """Build the read-only intelligence orchestration catalog. Metadata only."""
    now = utc_now_iso()
    stages: list[OrchestrationStage] = []
    if include_builtins:
        stages = [_as_stage(spec) for spec in _BUILTIN_STAGE_SPECS]

    return IntelligenceOrchestrator(
        orchestrator_id=f"intelligence_orchestrator_{now.replace(':', '').replace('-', '')}",
        schema_version=INTELLIGENCE_ORCHESTRATOR_SCHEMA_VERSION,
        stages=stages,
        generated_at=now,
        metadata=OrchestratorMetadata(
            legacy={"schema": INTELLIGENCE_ORCHESTRATOR_SCHEMA_VERSION},
            debug={
                "stage_count": len(stages),
                "ordered_stage_ids": [s.stage_id for s in stages],
            },
            custom={},
            future_extensions=empty_intelligence_orchestrator_future_extensions(),
        ),
    )
