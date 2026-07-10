from __future__ import annotations

from backend.models.ai_insight_models import UniversalAIInsightCollection, utc_now_iso
from backend.models.decision_models import DECISION_SCHEMA_VERSION, DecisionCollection
from backend.models.executive_reasoning_models import (
    EXECUTIVE_REASONING_SCHEMA_VERSION,
    ExecutiveReasoningCollection,
)
from backend.models.intelligence_bundle_models import (
    INTELLIGENCE_BUNDLE_SCHEMA_VERSION,
    IntelligenceBundle,
)
from backend.models.intelligence_registry_models import (
    CANONICAL_PIPELINE_TYPES,
    INTELLIGENCE_REGISTRY_SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
    DependencyEdge,
    DependencyGraph,
    IntelligenceRegistry,
    RegistryAsset,
    RegistryAssetStatus,
    RegistryMetadata,
    RegistryObjectType,
    RegistryStatistics,
    empty_intelligence_registry_future_extensions,
)
from backend.models.root_cause_models import RCA_SCHEMA_VERSION, RootCauseCollection
from backend.models.storyboard_models import STORYBOARD_SCHEMA_VERSION, ExecutiveStoryboard
from backend.models.validation_models import VALIDATION_ENGINE_VERSION, ValidationReport

# Canonical type-level edges (metadata only).
_TYPE_PIPELINE_EDGES: tuple[tuple[str, str], ...] = (
    ("insight", "validation"),
    ("validation", "decision"),
    ("decision", "root_cause"),
    ("root_cause", "executive_reasoning"),
    ("executive_reasoning", "storyboard"),
    ("storyboard", "intelligence_bundle"),
)

_PRODUCER_BY_TYPE: dict[RegistryObjectType, str] = {
    RegistryObjectType.insight: "ai_insight_mapper_service",
    RegistryObjectType.validation: "ai_validation_service",
    RegistryObjectType.decision: "decision_intelligence_service",
    RegistryObjectType.root_cause: "root_cause_analysis_service",
    RegistryObjectType.executive_reasoning: "executive_reasoning_service",
    RegistryObjectType.storyboard: "storyboard_engine_service",
    RegistryObjectType.intelligence_bundle: "intelligence_bundle_service",
}

_SUPPORTED_OBJECT_TYPES: frozenset[str] = frozenset(item.value for item in RegistryObjectType)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _validation_id(report: ValidationReport) -> str:
    return f"validation_{report.validator_version}_{report.validated_at}"


def _map_status(raw: object | None) -> RegistryAssetStatus:
    if raw is None:
        return RegistryAssetStatus.registered
    value = getattr(raw, "value", raw)
    text = str(value).lower()
    for status in RegistryAssetStatus:
        if status.value == text:
            return status
    return RegistryAssetStatus.unknown


def _detect_cycles(assets: list[RegistryAsset]) -> list[list[str]]:
    """Return dependency cycles as lists of object_ids. Metadata check only."""
    graph: dict[str, list[str]] = {asset.object_id: list(asset.dependencies) for asset in assets}
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

    for object_id in graph:
        dfs(object_id)
    return cycles


def _max_dependency_depth(assets: list[RegistryAsset]) -> int:
    """Longest dependency chain length among registered assets (metadata only)."""
    by_id = {asset.object_id: asset for asset in assets}
    memo: dict[str, int] = {}
    visiting: set[str] = set()

    def depth(object_id: str) -> int:
        if object_id in memo:
            return memo[object_id]
        if object_id in visiting:
            return 0  # cycle — depth undefined; treat as 0 for stats
        asset = by_id.get(object_id)
        if asset is None or not asset.dependencies:
            memo[object_id] = 0
            return 0
        visiting.add(object_id)
        best = 0
        for dep_id in asset.dependencies:
            if dep_id in by_id:
                best = max(best, 1 + depth(dep_id))
        visiting.remove(object_id)
        memo[object_id] = best
        return best

    if not assets:
        return 0
    return max(depth(asset.object_id) for asset in assets)


def find_asset(registry: IntelligenceRegistry, object_id: str) -> RegistryAsset | None:
    """Return a deep copy of one asset by object_id, or None."""
    for asset in registry.assets:
        if asset.object_id == object_id:
            return asset.model_copy(deep=True)
    return None


def list_assets(
    registry: IntelligenceRegistry,
    *,
    object_type: RegistryObjectType | str | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
    status: RegistryAssetStatus | str | None = None,
) -> list[RegistryAsset]:
    """Return deep-copied assets, optionally filtered by metadata fields."""
    type_value = object_type.value if isinstance(object_type, RegistryObjectType) else object_type
    status_value = status.value if isinstance(status, RegistryAssetStatus) else status
    results: list[RegistryAsset] = []
    for asset in registry.assets:
        if type_value is not None and asset.object_type.value != type_value:
            continue
        if dataset_id is not None and asset.dataset_id != dataset_id:
            continue
        if domain is not None and asset.domain != domain:
            continue
        if status_value is not None and asset.status.value != status_value:
            continue
        results.append(asset.model_copy(deep=True))
    return results


def register_asset(
    registry: IntelligenceRegistry,
    asset: RegistryAsset,
    *,
    replace: bool = True,
) -> IntelligenceRegistry:
    """Register or replace one metadata asset. Does not mutate the input registry."""
    copy = registry.model_copy(deep=True)
    assets = list(copy.assets)
    existing_idx = next((i for i, item in enumerate(assets) if item.object_id == asset.object_id), None)
    asset_copy = asset.model_copy(deep=True)
    if not asset_copy.reference_id:
        asset_copy.reference_id = asset_copy.object_id
    if not asset_copy.updated_at:
        asset_copy.updated_at = utc_now_iso()
    if existing_idx is None:
        assets.append(asset_copy)
    elif replace:
        assets[existing_idx] = asset_copy
    else:
        return copy

    copy.assets = assets
    copy.dependency_graph = dependency_graph(copy)
    return copy


def find_dependencies(registry: IntelligenceRegistry, object_id: str) -> list[str]:
    """Return direct dependency IDs for an asset (metadata only)."""
    for asset in registry.assets:
        if asset.object_id == object_id:
            return list(asset.dependencies)
    return []


def find_consumers(registry: IntelligenceRegistry, object_id: str) -> list[str]:
    """Return asset IDs that list object_id as a dependency."""
    consumers: list[str] = []
    for asset in registry.assets:
        if object_id in asset.dependencies:
            consumers.append(asset.object_id)
    for asset in registry.assets:
        if asset.object_id == object_id and asset.consumed_by:
            return _unique(list(asset.consumed_by) + consumers)
    return _unique(consumers)


def dependency_graph(registry: IntelligenceRegistry) -> DependencyGraph:
    """Build instance and type-level dependency graphs from registered assets."""
    by_id = {asset.object_id: asset for asset in registry.assets}
    nodes = [asset.object_id for asset in registry.assets]
    edges: list[DependencyEdge] = []

    for asset in registry.assets:
        for dep_id in asset.dependencies:
            dep = by_id.get(dep_id)
            edges.append(
                DependencyEdge(
                    from_id=asset.object_id,
                    to_id=dep_id,
                    from_type=asset.object_type.value,
                    to_type=dep.object_type.value if dep is not None else "",
                    edge_kind="depends_on",
                )
            )

    type_edges = [
        DependencyEdge(
            from_id=src,
            to_id=dst,
            from_type=src,
            to_type=dst,
            edge_kind="pipeline",
        )
        for src, dst in _TYPE_PIPELINE_EDGES
    ]

    return DependencyGraph(
        nodes=nodes,
        edges=edges,
        canonical_pipeline=list(CANONICAL_PIPELINE_TYPES),
        type_edges=type_edges,
    )


def validate_registry(registry: IntelligenceRegistry) -> dict[str, object]:
    """Structural integrity report only — never modifies assets."""
    issues: list[str] = []
    seen_ids: set[str] = set()
    asset_ids = {asset.object_id for asset in registry.assets}

    for asset in registry.assets:
        if not asset.object_id:
            issues.append("Asset missing object_id")
            continue
        if asset.object_id in seen_ids:
            issues.append(f"Duplicate object_id: {asset.object_id}")
        seen_ids.add(asset.object_id)

        if asset.object_type.value not in _SUPPORTED_OBJECT_TYPES:
            issues.append(f"Unsupported object_type: {asset.object_id} ({asset.object_type})")

        if asset.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            issues.append(
                f"Unsupported schema_version: {asset.object_id} ({asset.schema_version})"
            )

        if not asset.reference_id:
            issues.append(f"Missing reference_id: {asset.object_id}")

        if not asset.produced_by:
            issues.append(f"Missing produced_by: {asset.object_id}")

        if not asset.created_at:
            issues.append(f"Missing created_at: {asset.object_id}")

        for dep_id in asset.dependencies:
            if dep_id not in asset_ids:
                issues.append(f"Missing dependency asset: {asset.object_id} -> {dep_id}")

        for consumer_id in asset.consumed_by:
            if consumer_id not in asset_ids:
                issues.append(f"Missing consumer asset: {asset.object_id} <- {consumer_id}")

    for cycle in _detect_cycles(registry.assets):
        issues.append(f"Circular dependency: {' -> '.join(cycle)}")

    graph_nodes = set(registry.dependency_graph.nodes)
    if graph_nodes and graph_nodes != asset_ids:
        missing_in_graph = sorted(asset_ids - graph_nodes)
        extra_in_graph = sorted(graph_nodes - asset_ids)
        if missing_in_graph:
            issues.append(f"Graph missing nodes: {', '.join(missing_in_graph)}")
        if extra_in_graph:
            issues.append(f"Graph has unknown nodes: {', '.join(extra_in_graph)}")

    required_extensions = set(empty_intelligence_registry_future_extensions().keys())
    missing_extensions = sorted(required_extensions - set(registry.metadata.future_extensions.keys()))
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    expected_pipeline = list(CANONICAL_PIPELINE_TYPES)
    if registry.dependency_graph.canonical_pipeline != expected_pipeline:
        issues.append("canonical_pipeline does not match expected pipeline order")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "registry_id": registry.registry_id,
        "asset_count": len(registry.assets),
        "circular_dependencies": _detect_cycles(registry.assets),
    }


def registry_statistics(registry: IntelligenceRegistry) -> RegistryStatistics:
    """Catalog counts and graph shape only — no analytics or scoring."""
    assets_by_type: dict[str, int] = {}
    datasets: list[str] = []
    domains: list[str] = []
    status_counts: dict[str, int] = {}

    for asset in registry.assets:
        type_key = asset.object_type.value
        assets_by_type[type_key] = assets_by_type.get(type_key, 0) + 1
        if asset.dataset_id:
            datasets.append(asset.dataset_id)
        if asset.domain:
            domains.append(asset.domain)
        status_key = asset.status.value
        status_counts[status_key] = status_counts.get(status_key, 0) + 1

    root_nodes = [asset.object_id for asset in registry.assets if not asset.dependencies]
    leaf_nodes = [asset.object_id for asset in registry.assets if not asset.consumed_by]
    orphan_assets = [
        asset.object_id
        for asset in registry.assets
        if not asset.dependencies and not asset.consumed_by
    ]

    validation = validate_registry(registry)

    return RegistryStatistics(
        total_assets=len(registry.assets),
        assets_by_type=assets_by_type,
        datasets=sorted(set(datasets)),
        domains=sorted(set(domains)),
        dependency_depth=_max_dependency_depth(registry.assets),
        leaf_nodes=leaf_nodes,
        root_nodes=root_nodes,
        orphan_assets=orphan_assets,
        validation_summary={
            "valid": validation["valid"],
            "issue_count": validation["issue_count"],
            "status_counts": status_counts,
        },
    )


def _build_assets_from_sources(
    *,
    insights: UniversalAIInsightCollection | None,
    validations: list[ValidationReport] | None,
    decisions: DecisionCollection | None,
    root_causes: RootCauseCollection | None,
    reasonings: ExecutiveReasoningCollection | None,
    storyboard: ExecutiveStoryboard | None,
    bundle: IntelligenceBundle | None,
    dataset_id: str | None,
    domain: str | None,
    now: str,
) -> list[RegistryAsset]:
    """Extract metadata catalog records from existing objects. References only."""
    assets: list[RegistryAsset] = []
    insight_ids: list[str] = []
    validation_ids: list[str] = []
    decision_ids: list[str] = []
    root_cause_ids: list[str] = []
    reasoning_ids: list[str] = []
    storyboard_ids: list[str] = []

    if insights is not None:
        for item in insights.insights:
            insight_ids.append(item.id)
            assets.append(
                RegistryAsset(
                    object_id=item.id,
                    object_type=RegistryObjectType.insight,
                    schema_version=item.schema_version,
                    dataset_id=dataset_id or insights.dataset_id,
                    domain=domain or item.domain or insights.domain,
                    status=_map_status(item.validation_status),
                    dependencies=[],
                    produced_by=(
                        item.generated_by.engine
                        if item.generated_by
                        else _PRODUCER_BY_TYPE[RegistryObjectType.insight]
                    ),
                    consumed_by=[],
                    created_at=item.generated_at or now,
                    updated_at=item.generated_at or now,
                    reference_id=item.id,
                    metadata={
                        "title": item.title,
                        "priority": item.priority.value,
                        "risk_level": item.risk_level.value,
                    },
                )
            )

    if validations:
        for report in validations:
            vid = _validation_id(report)
            validation_ids.append(vid)
            assets.append(
                RegistryAsset(
                    object_id=vid,
                    object_type=RegistryObjectType.validation,
                    schema_version=report.validator_version or VALIDATION_ENGINE_VERSION,
                    dataset_id=dataset_id,
                    domain=domain,
                    status=_map_status(report.overall_status),
                    dependencies=list(insight_ids),
                    produced_by=_PRODUCER_BY_TYPE[RegistryObjectType.validation],
                    consumed_by=[],
                    created_at=report.validated_at or now,
                    updated_at=report.validated_at or now,
                    reference_id=vid,
                    metadata={"score": report.score, "validator_version": report.validator_version},
                )
            )

    if decisions is not None:
        for item in decisions.decisions:
            decision_ids.append(item.decision_id)
            deps = _unique(
                ([item.source_insight_id] if item.source_insight_id else [])
                + list(validation_ids)
                + list(item.depends_on)
            )
            assets.append(
                RegistryAsset(
                    object_id=item.decision_id,
                    object_type=RegistryObjectType.decision,
                    schema_version=item.schema_version or DECISION_SCHEMA_VERSION,
                    dataset_id=dataset_id or decisions.dataset_id or item.source_dataset,
                    domain=domain or decisions.domain,
                    status=_map_status(item.status),
                    dependencies=deps,
                    produced_by=_PRODUCER_BY_TYPE[RegistryObjectType.decision],
                    consumed_by=[],
                    created_at=item.generated_at or now,
                    updated_at=item.generated_at or now,
                    reference_id=item.decision_id,
                    metadata={
                        "source_insight_id": item.source_insight_id,
                        "priority": item.priority.value,
                        "category": item.category.value,
                    },
                )
            )

    if root_causes is not None:
        for item in root_causes.root_causes:
            root_cause_ids.append(item.root_cause_id)
            deps = _unique(
                ([item.source_insight_id] if item.source_insight_id else [])
                + ([item.source_decision_id] if item.source_decision_id else [])
                + list(validation_ids)
            )
            assets.append(
                RegistryAsset(
                    object_id=item.root_cause_id,
                    object_type=RegistryObjectType.root_cause,
                    schema_version=item.schema_version or RCA_SCHEMA_VERSION,
                    dataset_id=dataset_id or root_causes.dataset_id,
                    domain=domain or root_causes.domain,
                    status=RegistryAssetStatus.registered,
                    dependencies=deps,
                    produced_by=_PRODUCER_BY_TYPE[RegistryObjectType.root_cause],
                    consumed_by=[],
                    created_at=item.generated_at or now,
                    updated_at=item.generated_at or now,
                    reference_id=item.root_cause_id,
                    metadata={
                        "source_insight_id": item.source_insight_id,
                        "source_decision_id": item.source_decision_id,
                        "cause_category": item.cause_category.value,
                        "severity": item.severity.value,
                    },
                )
            )

    if reasonings is not None:
        for item in reasonings.reasonings:
            reasoning_ids.append(item.reasoning_id)
            deps = _unique(
                list(item.linked_insight_ids)
                + list(item.linked_decision_ids)
                + list(item.linked_root_cause_ids)
                + list(validation_ids)
                + list(item.metadata.linked_validation_report_ids)
            )
            assets.append(
                RegistryAsset(
                    object_id=item.reasoning_id,
                    object_type=RegistryObjectType.executive_reasoning,
                    schema_version=item.schema_version or EXECUTIVE_REASONING_SCHEMA_VERSION,
                    dataset_id=dataset_id or item.dataset_id or reasonings.dataset_id,
                    domain=domain or item.domain or reasonings.domain,
                    status=_map_status(item.overall_validation_status),
                    dependencies=deps,
                    produced_by=_PRODUCER_BY_TYPE[RegistryObjectType.executive_reasoning],
                    consumed_by=[],
                    created_at=item.generated_at or now,
                    updated_at=item.generated_at or now,
                    reference_id=item.reasoning_id,
                    metadata={"headline": item.headline, "reasoning_rank": item.reasoning_rank},
                )
            )

    if storyboard is not None:
        storyboard_ids.append(storyboard.storyboard_id)
        deps = _unique(
            list(storyboard.metadata.linked_insight_ids)
            + list(storyboard.metadata.linked_decision_ids)
            + list(storyboard.metadata.linked_root_cause_ids)
            + list(storyboard.metadata.linked_validation_report_ids)
            + list(storyboard.metadata.linked_reasoning_ids)
            + list(reasoning_ids)
        )
        assets.append(
            RegistryAsset(
                object_id=storyboard.storyboard_id,
                object_type=RegistryObjectType.storyboard,
                schema_version=storyboard.schema_version or STORYBOARD_SCHEMA_VERSION,
                dataset_id=dataset_id or storyboard.dataset_id,
                domain=domain or storyboard.domain,
                status=_map_status(storyboard.summary.validation_status),
                dependencies=deps,
                produced_by=_PRODUCER_BY_TYPE[RegistryObjectType.storyboard],
                consumed_by=[],
                created_at=storyboard.generated_at or now,
                updated_at=storyboard.generated_at or now,
                reference_id=storyboard.storyboard_id,
                metadata={"title": storyboard.title, "slide_count": len(storyboard.slides)},
            )
        )

    if bundle is not None:
        deps = _unique(
            list(bundle.references.insight_ids)
            + list(bundle.references.validation_ids)
            + list(bundle.references.decision_ids)
            + list(bundle.references.root_cause_ids)
            + list(bundle.references.reasoning_ids)
            + list(bundle.references.storyboard_ids)
            + list(insight_ids)
            + list(validation_ids)
            + list(decision_ids)
            + list(root_cause_ids)
            + list(reasoning_ids)
            + list(storyboard_ids)
        )
        assets.append(
            RegistryAsset(
                object_id=bundle.bundle_id,
                object_type=RegistryObjectType.intelligence_bundle,
                schema_version=bundle.schema_version or INTELLIGENCE_BUNDLE_SCHEMA_VERSION,
                dataset_id=dataset_id or bundle.dataset_id,
                domain=domain or bundle.domain,
                status=RegistryAssetStatus.registered,
                dependencies=deps,
                produced_by=_PRODUCER_BY_TYPE[RegistryObjectType.intelligence_bundle],
                consumed_by=[],
                created_at=bundle.generated_at or now,
                updated_at=bundle.generated_at or now,
                reference_id=bundle.bundle_id,
                metadata={
                    "summary_totals": {
                        "insights": bundle.summary.total_insights,
                        "decisions": bundle.summary.total_decisions,
                        "root_causes": bundle.summary.total_root_causes,
                        "storyboards": bundle.summary.total_storyboards,
                    }
                },
            )
        )

    consumers: dict[str, list[str]] = {asset.object_id: [] for asset in assets}
    for asset in assets:
        for dep_id in asset.dependencies:
            if dep_id in consumers:
                consumers[dep_id].append(asset.object_id)

    for asset in assets:
        asset.consumed_by = _unique(consumers.get(asset.object_id, []))

    return assets


def build_registry(
    *,
    insights: UniversalAIInsightCollection | None = None,
    validations: list[ValidationReport] | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    storyboard: ExecutiveStoryboard | None = None,
    bundle: IntelligenceBundle | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> IntelligenceRegistry:
    """Build a metadata catalog from existing intelligence assets.

    Does not run engines, orchestrate pipelines, or store payloads.
    """
    insights_c = insights.model_copy(deep=True) if insights is not None else None
    decisions_c = decisions.model_copy(deep=True) if decisions is not None else None
    root_causes_c = root_causes.model_copy(deep=True) if root_causes is not None else None
    reasonings_c = reasonings.model_copy(deep=True) if reasonings is not None else None
    storyboard_c = storyboard.model_copy(deep=True) if storyboard is not None else None
    bundle_c = bundle.model_copy(deep=True) if bundle is not None else None
    validations_c = [item.model_copy(deep=True) for item in (validations or [])]

    resolved_dataset = dataset_id
    resolved_domain = domain
    for source in (insights_c, decisions_c, root_causes_c, reasonings_c, storyboard_c, bundle_c):
        if source is None:
            continue
        if resolved_dataset is None and getattr(source, "dataset_id", None):
            resolved_dataset = source.dataset_id
        if resolved_domain is None and getattr(source, "domain", None):
            resolved_domain = source.domain

    now = utc_now_iso()
    assets = _build_assets_from_sources(
        insights=insights_c,
        validations=validations_c,
        decisions=decisions_c,
        root_causes=root_causes_c,
        reasonings=reasonings_c,
        storyboard=storyboard_c,
        bundle=bundle_c,
        dataset_id=resolved_dataset,
        domain=resolved_domain,
        now=now,
    )

    registry = IntelligenceRegistry(
        registry_id=f"registry_{resolved_dataset or 'empty'}_{now.replace(':', '').replace('-', '')}",
        schema_version=INTELLIGENCE_REGISTRY_SCHEMA_VERSION,
        dataset_id=resolved_dataset,
        domain=resolved_domain,
        assets=assets,
        dependency_graph=DependencyGraph(),
        generated_at=now,
        metadata=RegistryMetadata(
            legacy={"schema": INTELLIGENCE_REGISTRY_SCHEMA_VERSION},
            debug={
                "asset_count": len(assets),
                "types_present": sorted({a.object_type.value for a in assets}),
            },
            custom={},
            future_extensions=empty_intelligence_registry_future_extensions(),
        ),
    )
    registry.dependency_graph = dependency_graph(registry)
    return registry
