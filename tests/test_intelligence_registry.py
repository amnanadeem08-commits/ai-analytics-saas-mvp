from __future__ import annotations

from backend.models.ai_insight_models import (
    AI_INSIGHT_SCHEMA_VERSION,
    DataQualityScore,
    EffortLevel,
    InsightMetadata,
    InsightPriority,
    InsightProvenance,
    RecommendedAction,
    RiskLevel,
    SupportingEvidenceItem,
    UniversalAIInsight,
    UniversalAIInsightCollection,
    UrgencyLevel,
    ValidationStatus,
    utc_now_iso,
)
from backend.models.intelligence_registry_models import (
    CANONICAL_PIPELINE_TYPES,
    INTELLIGENCE_REGISTRY_FUTURE_EXTENSION_KEYS,
    RegistryAsset,
    RegistryAssetStatus,
    RegistryObjectType,
)
from backend.services.ai_validation_service import validate_insight
from backend.services.decision_intelligence_service import build_decision, build_decision_collection
from backend.services.executive_reasoning_service import build_executive_reasoning, build_reasoning_collection
from backend.services.intelligence_bundle_service import build_intelligence_bundle
from backend.services.intelligence_registry_service import (
    build_registry,
    dependency_graph,
    find_asset,
    find_consumers,
    find_dependencies,
    list_assets,
    register_asset,
    registry_statistics,
    validate_registry,
)
from backend.services.root_cause_analysis_service import build_root_cause, build_root_cause_collection
from backend.services.storyboard_engine_service import build_executive_storyboard_from_reasoning


def _base_insight(**overrides) -> UniversalAIInsight:
    insight = UniversalAIInsight(
        id="insight_registry",
        schema_version=AI_INSIGHT_SCHEMA_VERSION,
        title="Revenue decline in North",
        summary="North region revenue declined versus prior period.",
        insight="North region revenue declined versus prior period.",
        reason="North segment totals are consistently lower than East.",
        supporting_evidence=[
            SupportingEvidenceItem(
                label="North revenue total",
                value=42000,
                evidence_type="metric",
                source="validated_kpi",
                confidence_score=0.9,
            )
        ],
        affected_metrics=["revenue"],
        business_impact="Lower revenue concentration increases downside risk.",
        expected_outcome="Stabilize North performance.",
        risk_level=RiskLevel.high,
        priority=InsightPriority.high,
        recommended_actions=[
            RecommendedAction(
                action="Investigate North region sales execution.",
                rationale="North is the weakest validated segment.",
                expected_outcome="Identify operational drivers.",
                estimated_effort=EffortLevel.medium,
                urgency=UrgencyLevel.high,
            )
        ],
        data_confidence=0.88,
        reasoning_confidence=0.84,
        overall_confidence=0.86,
        confidence_reason="Validated KPI and segment evidence.",
        assumptions=["Revenue field is complete."],
        limitations=["No causal experiment has been run."],
        related_kpis=["total_revenue"],
        domain="Sales",
        generated_by=InsightProvenance(engine="test", provider="platform", engine_version="1.0.0"),
        generated_at=utc_now_iso(),
        validation_status=ValidationStatus.validated,
        data_quality_score=DataQualityScore(
            score=90.0, grade="A", completeness_pct=97.0, dimensions={"freshness": "good"}
        ),
        metadata=InsightMetadata(custom={"dataset_id": "sales_q1"}),
    )
    return insight.model_copy(update=overrides)


def _full_pipeline():
    insight = _base_insight()
    validated, report = validate_insight(insight)
    decision = build_decision(validated)
    root_cause = build_root_cause(insight=validated, decision=decision)
    reasoning = build_executive_reasoning(
        insight=validated,
        decision=decision,
        root_cause=root_cause,
        validation=report,
        dataset_id="sales_q1",
        domain="Sales",
    )
    insights = UniversalAIInsightCollection(dataset_id="sales_q1", domain="Sales", insights=[validated])
    decisions = build_decision_collection([validated], dataset_id="sales_q1", domain="Sales")
    root_causes = build_root_cause_collection(
        insights=[validated],
        decisions=[decision],
        dataset_id="sales_q1",
        domain="Sales",
    )
    reasonings = build_reasoning_collection(reasonings=[reasoning], dataset_id="sales_q1", domain="Sales")
    storyboard = build_executive_storyboard_from_reasoning(
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=[report],
        dataset_id="sales_q1",
        domain="Sales",
    )
    bundle = build_intelligence_bundle(
        insights=insights,
        validations=[report],
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        dataset_id="sales_q1",
        domain="Sales",
    )
    return insights, [report], decisions, root_causes, reasonings, storyboard, bundle


def test_registry_creation():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle = _full_pipeline()
    registry = build_registry(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
        dataset_id="sales_q1",
        domain="Sales",
    )

    types = {asset.object_type for asset in registry.assets}
    assert RegistryObjectType.insight in types
    assert RegistryObjectType.validation in types
    assert RegistryObjectType.decision in types
    assert RegistryObjectType.root_cause in types
    assert RegistryObjectType.executive_reasoning in types
    assert RegistryObjectType.storyboard in types
    assert RegistryObjectType.intelligence_bundle in types
    assert registry.dataset_id == "sales_q1"
    assert registry.domain == "Sales"
    assert len(registry.assets) >= 7
    assert all(asset.reference_id for asset in registry.assets)


def test_asset_registration_and_find_list():
    registry = build_registry()
    now = utc_now_iso()
    asset = RegistryAsset(
        object_id="manual_insight",
        object_type=RegistryObjectType.insight,
        schema_version="1.0.0",
        dataset_id="sales_q1",
        domain="Sales",
        status=RegistryAssetStatus.registered,
        produced_by="test",
        created_at=now,
        updated_at=now,
        reference_id="manual_insight",
        metadata={"note": "catalog-only"},
    )
    updated = register_asset(registry, asset)
    assert registry.assets == []
    found = find_asset(updated, "manual_insight")
    assert found is not None
    assert found.metadata["note"] == "catalog-only"
    listed = list_assets(updated, object_type=RegistryObjectType.insight, dataset_id="sales_q1")
    assert len(listed) == 1
    assert list_assets(updated, object_type=RegistryObjectType.decision) == []


def test_reference_integrity():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle = _full_pipeline()
    registry = build_registry(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
    )
    for asset in registry.assets:
        assert asset.reference_id == asset.object_id
        assert asset.produced_by
        assert asset.created_at
        # Catalog only — no payload fields that look like full objects.
        assert "insights" not in asset.metadata
        assert "decisions" not in asset.metadata
        assert "slides" not in asset.metadata or isinstance(asset.metadata.get("slide_count"), int)


def test_dependency_graph():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle = _full_pipeline()
    registry = build_registry(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
    )
    graph = dependency_graph(registry)

    assert graph.canonical_pipeline == list(CANONICAL_PIPELINE_TYPES)
    assert len(graph.type_edges) == 6
    assert graph.type_edges[0].from_id == "insight"
    assert graph.type_edges[-1].to_id == "intelligence_bundle"
    assert set(graph.nodes) == {asset.object_id for asset in registry.assets}
    assert graph.edges


def test_dependency_and_consumer_lookup():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle = _full_pipeline()
    registry = build_registry(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
    )
    insight_id = insights.insights[0].id
    decision_id = decisions.decisions[0].decision_id

    assert insight_id in find_dependencies(registry, decision_id)
    assert find_consumers(registry, insight_id)
    assert bundle.bundle_id in find_consumers(registry, storyboard.storyboard_id) or any(
        asset.object_type == RegistryObjectType.intelligence_bundle
        and storyboard.storyboard_id in asset.dependencies
        for asset in registry.assets
    )


def test_registry_statistics():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle = _full_pipeline()
    registry = build_registry(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
        dataset_id="sales_q1",
        domain="Sales",
    )
    stats = registry_statistics(registry)
    assert stats.total_assets == len(registry.assets)
    assert stats.assets_by_type.get("insight") == 1
    assert "sales_q1" in stats.datasets
    assert "Sales" in stats.domains
    assert stats.dependency_depth >= 1
    assert stats.root_nodes
    assert stats.leaf_nodes
    assert "valid" in stats.validation_summary


def test_validate_registry():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle = _full_pipeline()
    registry = build_registry(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
    )
    result = validate_registry(registry)
    assert result["valid"] is True
    assert result["asset_count"] == len(registry.assets)
    assert result["circular_dependencies"] == []


def test_missing_and_partial_assets():
    empty = build_registry()
    assert empty.assets == []
    assert validate_registry(empty)["valid"] is True
    empty_stats = registry_statistics(empty)
    assert empty_stats.total_assets == 0
    assert empty_stats.dependency_depth == 0

    insights, validations, _, _, _, _, _ = _full_pipeline()
    partial = build_registry(insights=insights, validations=validations, dataset_id="sales_q1")
    types = {asset.object_type for asset in partial.assets}
    assert RegistryObjectType.insight in types
    assert RegistryObjectType.validation in types
    assert RegistryObjectType.decision not in types
    assert RegistryObjectType.intelligence_bundle not in types
    assert validate_registry(partial)["valid"] is True


def test_duplicate_ids():
    registry = build_registry()
    now = utc_now_iso()
    first = RegistryAsset(
        object_id="dup_id",
        object_type=RegistryObjectType.insight,
        schema_version="1.0.0",
        produced_by="test",
        created_at=now,
        updated_at=now,
        reference_id="dup_id",
    )
    second = first.model_copy(update={"metadata": {"copy": True}})
    with_one = register_asset(registry, first)
    with_two = register_asset(with_one, second, replace=False)
    # replace=False leaves original; force a duplicate for validation by appending manually
    broken = with_one.model_copy(deep=True)
    broken.assets = list(broken.assets) + [second.model_copy(deep=True)]
    result = validate_registry(broken)
    assert result["valid"] is False
    assert any("Duplicate object_id" in issue for issue in result["issues"])
    assert len(with_two.assets) == 1


def test_circular_dependency_detection():
    now = utc_now_iso()
    a = RegistryAsset(
        object_id="a",
        object_type=RegistryObjectType.insight,
        schema_version="1.0.0",
        dependencies=["b"],
        produced_by="test",
        created_at=now,
        updated_at=now,
        reference_id="a",
    )
    b = RegistryAsset(
        object_id="b",
        object_type=RegistryObjectType.validation,
        schema_version="1.0.0",
        dependencies=["a"],
        produced_by="test",
        created_at=now,
        updated_at=now,
        reference_id="b",
    )
    registry = build_registry()
    registry = register_asset(registry, a)
    registry = register_asset(registry, b)
    # Fix consumed_by for structural consistency of the cycle case
    registry = registry.model_copy(
        update={
            "assets": [
                a.model_copy(update={"consumed_by": ["b"]}, deep=True),
                b.model_copy(update={"consumed_by": ["a"]}, deep=True),
            ]
        },
        deep=True,
    )
    registry = registry.model_copy(update={"dependency_graph": dependency_graph(registry)}, deep=True)
    result = validate_registry(registry)
    assert result["valid"] is False
    assert result["circular_dependencies"]
    assert any("Circular dependency" in issue for issue in result["issues"])


def test_metadata_preservation_and_future_extensions():
    registry = build_registry()
    for key in INTELLIGENCE_REGISTRY_FUTURE_EXTENSION_KEYS:
        assert key in registry.metadata.future_extensions
        assert registry.metadata.future_extensions[key] == {}
    assert "event_bus" in registry.metadata.future_extensions
    assert "lineage" in registry.metadata.future_extensions
    assert "observability" in registry.metadata.future_extensions
    assert registry.metadata.debug["asset_count"] == 0

    now = utc_now_iso()
    asset = RegistryAsset(
        object_id="meta_asset",
        object_type=RegistryObjectType.insight,
        schema_version="1.0.0",
        produced_by="test",
        created_at=now,
        updated_at=now,
        reference_id="meta_asset",
        metadata={"custom_flag": True, "tags": ["a", "b"]},
    )
    updated = register_asset(registry, asset)
    found = find_asset(updated, "meta_asset")
    assert found is not None
    assert found.metadata == {"custom_flag": True, "tags": ["a", "b"]}


def test_immutability():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle = _full_pipeline()
    snapshots = (
        insights.model_dump(),
        validations[0].model_dump(),
        decisions.model_dump(),
        root_causes.model_dump(),
        reasonings.model_dump(),
        storyboard.model_dump(),
        bundle.model_dump(),
    )
    registry = build_registry(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
    )
    assert insights.model_dump() == snapshots[0]
    assert validations[0].model_dump() == snapshots[1]
    assert decisions.model_dump() == snapshots[2]
    assert root_causes.model_dump() == snapshots[3]
    assert reasonings.model_dump() == snapshots[4]
    assert storyboard.model_dump() == snapshots[5]
    assert bundle.model_dump() == snapshots[6]

    original_assets = [a.model_dump() for a in registry.assets]
    find_asset(registry, registry.assets[0].object_id)
    list_assets(registry)
    registry_statistics(registry)
    validate_registry(registry)
    assert [a.model_dump() for a in registry.assets] == original_assets


def test_broken_dependency_validation():
    registry = build_registry()
    asset = RegistryAsset(
        object_id="manual_asset",
        object_type=RegistryObjectType.insight,
        schema_version="1.0.0",
        dataset_id="sales_q1",
        domain="Sales",
        status=RegistryAssetStatus.registered,
        dependencies=["missing_dep"],
        produced_by="test",
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        reference_id="manual_asset",
        metadata={"note": "manual"},
    )
    updated = register_asset(registry, asset)
    result = validate_registry(updated)
    assert result["valid"] is False
    assert any("Missing dependency" in issue for issue in result["issues"])
