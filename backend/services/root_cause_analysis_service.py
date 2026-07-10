from __future__ import annotations

from typing import Any

from backend.models.ai_insight_models import (
    RiskLevel,
    UniversalAIInsight,
    ValidationStatus,
    utc_now_iso,
)
from backend.models.decision_models import DecisionRecommendation, DecisionStatus
from backend.models.root_cause_models import (
    RCA_SCHEMA_VERSION,
    CauseCategory,
    CauseChain,
    CauseEvidence,
    CauseMetadata,
    CauseNode,
    CauseOrigin,
    CauseSeverity,
    CauseStatus,
    CauseSummary,
    ProbabilitySource,
    RootCause,
    RootCauseCollection,
    severity_from_risk,
)

_PENDING_MESSAGE = "Insight must be validated before root cause analysis can run."
_MAX_CHAIN_DEPTH = 4

_DOMAIN_CATEGORY_MAP: dict[str, CauseCategory] = {
    "sales": CauseCategory.sales,
    "marketing": CauseCategory.marketing,
    "finance": CauseCategory.finance,
    "financial": CauseCategory.finance,
    "operations": CauseCategory.operations,
    "inventory": CauseCategory.inventory,
    "supply chain": CauseCategory.supply_chain,
    "customer churn": CauseCategory.customer,
    "telecom": CauseCategory.customer,
    "healthcare": CauseCategory.customer,
    "insurance": CauseCategory.compliance,
    "generic business dataset": CauseCategory.other,
}

_KEYWORD_CATEGORY_RULES: tuple[tuple[str, CauseCategory], ...] = (
    ("sales", CauseCategory.sales),
    ("revenue", CauseCategory.sales),
    ("marketing", CauseCategory.marketing),
    ("campaign", CauseCategory.marketing),
    ("finance", CauseCategory.finance),
    ("margin", CauseCategory.finance),
    ("cost", CauseCategory.finance),
    ("operations", CauseCategory.operations),
    ("operational", CauseCategory.operations),
    ("inventory", CauseCategory.inventory),
    ("stock", CauseCategory.inventory),
    ("supply", CauseCategory.supply_chain),
    ("supplier", CauseCategory.supply_chain),
    ("customer", CauseCategory.customer),
    ("churn", CauseCategory.customer),
    ("pricing", CauseCategory.pricing),
    ("price", CauseCategory.pricing),
    ("quality", CauseCategory.quality),
    ("defect", CauseCategory.quality),
    ("data quality", CauseCategory.data_quality),
    ("missing", CauseCategory.data_quality),
    ("completeness", CauseCategory.data_quality),
    ("external", CauseCategory.external_factors),
    ("market", CauseCategory.external_factors),
    ("compliance", CauseCategory.compliance),
    ("regulatory", CauseCategory.compliance),
)

_SEVERITY_SCORE_BOOST = {
    CauseSeverity.critical: 15.0,
    CauseSeverity.high: 10.0,
    CauseSeverity.medium: 5.0,
    CauseSeverity.low: 2.0,
    CauseSeverity.info: 0.0,
}


def _require_validated_insight(insight: UniversalAIInsight | None) -> None:
    if insight is None:
        return
    if insight.validation_status == ValidationStatus.pending:
        raise ValueError(_PENDING_MESSAGE)


def _text_blob(insight: UniversalAIInsight | None, decision: DecisionRecommendation | None) -> str:
    parts: list[str] = []
    if insight is not None:
        parts.extend(
            [
                insight.title,
                insight.summary,
                insight.insight,
                insight.reason,
                insight.business_impact,
                str(insight.metadata.legacy.get("type", "")),
                str(insight.metadata.custom.get("cause_category", "")),
            ]
        )
    if decision is not None:
        parts.extend(
            [
                decision.title,
                decision.summary,
                decision.business_reason,
                decision.business_impact,
                decision.category.value,
            ]
        )
    return " ".join(parts).lower()


def infer_cause_category(
    insight: UniversalAIInsight | None = None,
    decision: DecisionRecommendation | None = None,
) -> tuple[CauseCategory, str]:
    """Deterministic category inference: metadata → domain → risk → keywords."""
    if insight is not None:
        metadata_category = insight.metadata.custom.get("cause_category") or insight.metadata.legacy.get("cause_category")
        if metadata_category:
            for category in CauseCategory:
                if category.value.lower() == str(metadata_category).lower() or category.name == str(metadata_category).lower():
                    return category, "metadata"

    if decision is not None:
        decision_category = decision.metadata.custom.get("cause_category")
        if decision_category:
            for category in CauseCategory:
                if category.value.lower() == str(decision_category).lower() or category.name == str(decision_category).lower():
                    return category, "metadata"

    domain = (insight.domain if insight else None) or (decision.metadata.custom.get("domain") if decision else None)
    if domain:
        domain_key = str(domain).strip().lower()
        if domain_key in _DOMAIN_CATEGORY_MAP:
            return _DOMAIN_CATEGORY_MAP[domain_key], "domain"

    risk = None
    if insight is not None:
        risk = insight.risk_level
    elif decision is not None:
        risk = decision.risk_level
    if risk in {RiskLevel.high, RiskLevel.critical}:
        return CauseCategory.operations, "risk"

    blob = _text_blob(insight, decision)
    for keyword, category in _KEYWORD_CATEGORY_RULES:
        if keyword in blob:
            return category, "keywords"

    return CauseCategory.other, "keywords"


def _map_evidence_from_insight(insight: UniversalAIInsight) -> list[CauseEvidence]:
    return [
        CauseEvidence(
            label=item.label,
            value=item.value,
            evidence_type=item.evidence_type,
            source=item.source,
            confidence_score=item.confidence_score,
            raw=item.raw,
        )
        for item in insight.supporting_evidence
    ]


def _map_evidence_from_decision(decision: DecisionRecommendation) -> list[CauseEvidence]:
    return [
        CauseEvidence(
            label=item.label,
            value=item.value,
            evidence_type=item.evidence_type,
            source=item.source,
            confidence_score=item.confidence_score,
            raw=item.raw,
        )
        for item in decision.supporting_evidence
    ]


def _collect_evidence(
    insight: UniversalAIInsight | None,
    decision: DecisionRecommendation | None,
) -> list[CauseEvidence]:
    evidence: list[CauseEvidence] = []
    if insight is not None:
        evidence.extend(_map_evidence_from_insight(insight))
    if decision is not None and not evidence:
        evidence.extend(_map_evidence_from_decision(decision))
    elif decision is not None and evidence:
        # Prefer insight evidence; append decision evidence only when labels differ.
        existing = {item.label for item in evidence}
        for item in _map_evidence_from_decision(decision):
            if item.label not in existing:
                evidence.append(item)
    return evidence


def _resolve_probability(
    insight: UniversalAIInsight | None,
    decision: DecisionRecommendation | None,
) -> tuple[float | None, ProbabilitySource]:
    """Probability is never copied from confidence. Defaults to None."""
    for source in (insight, decision):
        if source is None:
            continue
        custom = source.metadata.custom
        if "probability" in custom and custom.get("probability") is not None:
            try:
                value = float(custom["probability"])
            except (TypeError, ValueError):
                continue
            if 0.0 <= value <= 1.0:
                raw_source = str(custom.get("probability_source") or "estimated").lower()
                for option in ProbabilitySource:
                    if option.value == raw_source or option.name == raw_source:
                        return value, option
                return value, ProbabilitySource.estimated
    return None, ProbabilitySource.unknown


def _determine_origin(
    insight: UniversalAIInsight | None,
    decision: DecisionRecommendation | None,
    evidence: list[CauseEvidence],
    used_metadata_drivers: bool,
) -> CauseOrigin:
    sources: set[CauseOrigin] = set()
    if insight is not None and (insight.reason.strip() or insight.title.strip()):
        sources.add(CauseOrigin.insight)
    if decision is not None and decision.business_reason.strip():
        sources.add(CauseOrigin.decision)
    if evidence:
        sources.add(CauseOrigin.evidence)
    if used_metadata_drivers:
        sources.add(CauseOrigin.metadata)
    if len(sources) > 1:
        return CauseOrigin.mixed
    if sources:
        return next(iter(sources))
    if insight is not None:
        return CauseOrigin.insight
    if decision is not None:
        return CauseOrigin.decision
    return CauseOrigin.metadata


def _evaluate_status(
    *,
    insight: UniversalAIInsight | None,
    decision: DecisionRecommendation | None,
    description: str,
    evidence: list[CauseEvidence],
) -> CauseStatus:
    if insight is not None and insight.validation_status == ValidationStatus.rejected:
        return CauseStatus.blocked
    if decision is not None and decision.status == DecisionStatus.blocked:
        return CauseStatus.blocked
    if not description.strip() or not evidence:
        return CauseStatus.inconclusive
    return CauseStatus.identified


def compute_traceability_score(
    *,
    evidence: list[CauseEvidence],
    description: str,
    validation_status: ValidationStatus,
    chain_depth: int,
    used_metadata_drivers: bool,
) -> float:
    """0–100 measure of how strongly a cause is supported by validated evidence."""
    score = 0.0
    if description.strip():
        score += 20.0
    score += min(len(evidence) * 15.0, 45.0)
    sourced = sum(1 for item in evidence if str(item.source or "").strip())
    score += min(sourced * 5.0, 15.0)
    if validation_status == ValidationStatus.validated:
        score += 15.0
    elif validation_status == ValidationStatus.insufficient:
        score += 5.0
    score += min(max(chain_depth - 1, 0) * 3.0, 9.0)
    if used_metadata_drivers:
        score += 5.0
    return round(max(0.0, min(100.0, score)), 2)


def compute_cause_score(
    *,
    confidence: float,
    severity: CauseSeverity,
    status: CauseStatus,
    validation_status: ValidationStatus,
    evidence_count: int,
    chain_depth: int,
) -> float:
    if status == CauseStatus.blocked:
        return 0.0
    score = confidence * 50.0
    score += min(evidence_count * 8.0, 24.0)
    score += _SEVERITY_SCORE_BOOST.get(severity, 0.0)
    if validation_status == ValidationStatus.validated:
        score += 10.0
    elif validation_status == ValidationStatus.insufficient:
        score -= 5.0
    score += min(max(chain_depth - 1, 0) * 5.0, 10.0)
    if status == CauseStatus.inconclusive:
        score -= 20.0
    return round(max(0.0, min(100.0, score)), 2)


def _link_parent_child(parent: CauseNode, child: CauseNode) -> None:
    if child.node_id not in parent.child_ids:
        parent.child_ids.append(child.node_id)
    if parent.node_id not in child.parent_ids:
        child.parent_ids.append(parent.node_id)


def build_cause_chain(
    insight: UniversalAIInsight | None = None,
    decision: DecisionRecommendation | None = None,
    *,
    root_cause_id: str | None = None,
) -> CauseChain:
    """Build a hierarchical cause chain (tree today; nodes are graph-ready)."""
    if insight is None and decision is None:
        raise ValueError("At least one of insight or decision is required.")
    _require_validated_insight(insight)

    outcome_title = (insight.title if insight else decision.title) if (insight or decision) else "Outcome"
    source_key = (insight.id if insight else decision.decision_id) if (insight or decision) else "unknown"
    chain_id = f"chain_{root_cause_id or source_key}"

    nodes: list[CauseNode] = []
    outcome = CauseNode(
        node_id=f"{chain_id}_n0",
        parent_ids=[],
        child_ids=[],
        level=0,
        description=outcome_title,
        confidence=(insight.overall_confidence if insight else decision.confidence) if (insight or decision) else 0.0,
        evidence=[],
        metadata=CauseMetadata(legacy={"role": "outcome"}),
    )
    nodes.append(outcome)
    current_parent = outcome

    reason = ""
    if insight is not None and insight.reason.strip():
        reason = insight.reason.strip()
    elif decision is not None and decision.business_reason.strip():
        reason = decision.business_reason.strip()

    if reason and len(nodes) < _MAX_CHAIN_DEPTH:
        reason_node = CauseNode(
            node_id=f"{chain_id}_n1",
            parent_ids=[],
            child_ids=[],
            level=1,
            description=reason,
            confidence=(insight.overall_confidence if insight else decision.confidence) if (insight or decision) else 0.0,
            evidence=[],
            metadata=CauseMetadata(legacy={"role": "business_reason"}),
        )
        _link_parent_child(current_parent, reason_node)
        nodes.append(reason_node)
        current_parent = reason_node

    evidence = _collect_evidence(insight, decision)
    for index, item in enumerate(evidence):
        if len(nodes) >= _MAX_CHAIN_DEPTH:
            break
        evidence_node = CauseNode(
            node_id=f"{chain_id}_e{index}",
            parent_ids=[],
            child_ids=[],
            level=current_parent.level + 1,
            description=f"{item.label}: {item.value}",
            confidence=float(item.confidence_score) if item.confidence_score is not None else (
                insight.overall_confidence if insight else decision.confidence
            ),
            evidence=[item],
            metadata=CauseMetadata(legacy={"role": "evidence", "index": index}),
        )
        _link_parent_child(current_parent, evidence_node)
        nodes.append(evidence_node)
        current_parent = evidence_node

    driver_facts: list[Any] = []
    if insight is not None:
        raw_drivers = insight.metadata.custom.get("driver_facts")
        if isinstance(raw_drivers, list):
            driver_facts = raw_drivers
    if decision is not None and not driver_facts:
        raw_drivers = decision.metadata.custom.get("driver_facts")
        if isinstance(raw_drivers, list):
            driver_facts = raw_drivers

    for index, driver in enumerate(driver_facts):
        if len(nodes) >= _MAX_CHAIN_DEPTH:
            break
        if isinstance(driver, dict):
            description = str(driver.get("description") or driver.get("driver") or driver.get("label") or "").strip()
            confidence = float(driver.get("confidence", current_parent.confidence) or 0.0)
            evidence_items = []
            if description:
                evidence_items = [
                    CauseEvidence(
                        label=str(driver.get("label") or f"Driver {index + 1}"),
                        value=driver.get("value", description),
                        evidence_type=str(driver.get("evidence_type") or "driver_fact"),
                        source=str(driver.get("source") or "metadata.custom.driver_facts"),
                        confidence_score=confidence if confidence else None,
                        raw=driver,
                    )
                ]
        else:
            description = str(driver).strip()
            confidence = current_parent.confidence
            evidence_items = [
                CauseEvidence(
                    label=f"Driver {index + 1}",
                    value=description,
                    evidence_type="driver_fact",
                    source="metadata.custom.driver_facts",
                )
            ] if description else []
        if not description:
            continue
        driver_node = CauseNode(
            node_id=f"{chain_id}_d{index}",
            parent_ids=[],
            child_ids=[],
            level=current_parent.level + 1,
            description=description,
            confidence=max(0.0, min(1.0, confidence)),
            evidence=evidence_items,
            metadata=CauseMetadata(legacy={"role": "driver_fact", "index": index}),
        )
        _link_parent_child(current_parent, driver_node)
        nodes.append(driver_node)
        current_parent = driver_node

    depth = max((node.level for node in nodes), default=0)
    primary_node_id = None
    for node in reversed(nodes):
        if node.level > 0 and (node.evidence or node.level == 1):
            primary_node_id = node.node_id
            break
    if primary_node_id is None and nodes:
        primary_node_id = nodes[0].node_id

    return CauseChain(
        chain_id=chain_id,
        outcome_title=outcome_title,
        nodes=nodes,
        primary_node_id=primary_node_id,
        depth=depth,
        metadata=CauseMetadata(debug={"max_depth": _MAX_CHAIN_DEPTH, "node_count": len(nodes)}),
    )


def build_root_cause(
    insight: UniversalAIInsight | None = None,
    decision: DecisionRecommendation | None = None,
) -> RootCause:
    """Convert validated insight and/or decision into a RootCause. Never fabricates causes."""
    if insight is None and decision is None:
        raise ValueError("At least one of insight or decision is required.")
    _require_validated_insight(insight)

    evidence = _collect_evidence(insight, decision)
    description = ""
    if insight is not None and insight.reason.strip():
        description = insight.reason.strip()
    elif decision is not None and decision.business_reason.strip():
        description = decision.business_reason.strip()

    title = ""
    if description:
        title = description.split(".")[0][:120]
    elif insight is not None:
        title = insight.title
    elif decision is not None:
        title = decision.title

    summary = (insight.summary if insight else "") or (decision.summary if decision else "")
    business_impact = (insight.business_impact if insight else "") or (decision.business_impact if decision else "")
    confidence = (insight.overall_confidence if insight else None)
    if confidence is None and decision is not None:
        confidence = decision.confidence
    confidence = float(confidence or 0.0)

    severity = severity_from_risk(
        insight.risk_level if insight is not None else (decision.risk_level if decision is not None else RiskLevel.info)
    )
    category, category_source = infer_cause_category(insight, decision)
    used_metadata_drivers = bool(
        (insight and isinstance(insight.metadata.custom.get("driver_facts"), list) and insight.metadata.custom.get("driver_facts"))
        or (decision and isinstance(decision.metadata.custom.get("driver_facts"), list) and decision.metadata.custom.get("driver_facts"))
    )
    origin = _determine_origin(insight, decision, evidence, used_metadata_drivers)
    status = _evaluate_status(insight=insight, decision=decision, description=description, evidence=evidence)
    validation_status = (
        insight.validation_status
        if insight is not None
        else (decision.validation_status if decision is not None else ValidationStatus.pending)
    )

    source_insight_id = insight.id if insight is not None else (decision.source_insight_id if decision else "")
    source_decision_id = decision.decision_id if decision is not None else ""
    root_cause_id = f"rca_{source_insight_id or source_decision_id or 'unknown'}"

    chain = build_cause_chain(insight, decision, root_cause_id=root_cause_id)
    probability, probability_source = _resolve_probability(insight, decision)

    affected_dimensions: list[str] = []
    if insight is not None:
        raw_dims = insight.metadata.custom.get("affected_dimensions")
        if isinstance(raw_dims, list):
            affected_dimensions = [str(item) for item in raw_dims if item]
    if decision is not None and not affected_dimensions:
        raw_dims = decision.metadata.custom.get("affected_dimensions")
        if isinstance(raw_dims, list):
            affected_dimensions = [str(item) for item in raw_dims if item]

    business_area = ""
    if insight is not None and insight.domain:
        business_area = insight.domain
    elif decision is not None:
        business_area = decision.category.value

    traceability = compute_traceability_score(
        evidence=evidence,
        description=description,
        validation_status=validation_status,
        chain_depth=chain.depth,
        used_metadata_drivers=used_metadata_drivers,
    )
    cause_score = compute_cause_score(
        confidence=confidence,
        severity=severity,
        status=status,
        validation_status=validation_status,
        evidence_count=len(evidence),
        chain_depth=chain.depth,
    )

    return RootCause(
        root_cause_id=root_cause_id,
        title=title or "Root cause",
        summary=summary,
        description=description,
        cause_category=category,
        severity=severity,
        confidence=confidence,
        probability=probability,
        probability_source=probability_source,
        cause_origin=origin,
        business_area=business_area,
        affected_metrics=list(insight.affected_metrics if insight else (decision.affected_metrics if decision else [])),
        affected_dimensions=affected_dimensions,
        related_kpis=list(insight.related_kpis if insight else (decision.related_kpis if decision else [])),
        related_charts=list(insight.related_charts if insight else (decision.related_charts if decision else [])),
        supporting_evidence=evidence,
        assumptions=list(insight.assumptions if insight else (decision.assumptions if decision else [])),
        limitations=list(insight.limitations if insight else (decision.limitations if decision else [])),
        business_impact=business_impact,
        source_insight_id=source_insight_id,
        source_decision_id=source_decision_id,
        cause_score=cause_score,
        traceability_score=traceability,
        status=status,
        validation_status=validation_status,
        generated_at=utc_now_iso(),
        metadata=CauseMetadata(
            legacy={"category_source": category_source, "chain_id": chain.chain_id},
            debug={"chain_depth": chain.depth, "primary_node_id": chain.primary_node_id},
            custom=dict(insight.metadata.custom) if insight else dict(decision.metadata.custom if decision else {}),
            future_extensions={
                "prediction": {},
                "simulation": {},
                "workflow": {},
                "approval": {},
                "automation": {},
            },
        ),
    )


def rank_root_causes(causes: list[RootCause]) -> list[RootCause]:
    ranked = sorted(
        causes,
        key=lambda item: (
            item.status != CauseStatus.identified,
            item.status == CauseStatus.blocked,
            -item.cause_score,
            -item.traceability_score,
            -item.confidence,
        ),
    )
    result: list[RootCause] = []
    for index, item in enumerate(ranked):
        result.append(
            item.model_copy(
                update={"cause_rank": index + 1, "is_primary": index == 0 and item.status == CauseStatus.identified},
                deep=True,
            )
        )
    return result


def find_primary_cause(causes: list[RootCause]) -> RootCause | None:
    ranked = rank_root_causes(causes)
    for item in ranked:
        if item.status == CauseStatus.identified and item.supporting_evidence:
            return item
    return ranked[0] if ranked else None


def find_contributing_factors(causes: list[RootCause]) -> list[RootCause]:
    ranked = rank_root_causes(causes)
    primary = find_primary_cause(causes)
    primary_id = primary.root_cause_id if primary else None
    return [
        item
        for item in ranked
        if item.root_cause_id != primary_id and item.confidence > 0 and item.status != CauseStatus.blocked
    ]


def group_by_category(causes: list[RootCause]) -> dict[str, list[RootCause]]:
    grouped: dict[str, list[RootCause]] = {}
    for cause in causes:
        key = cause.cause_category.value
        grouped.setdefault(key, []).append(cause.model_copy(deep=True))
    return grouped


def summarize_root_causes(causes: list[RootCause]) -> CauseSummary:
    ranked = rank_root_causes(causes)
    primary = find_primary_cause(causes)
    contributing = find_contributing_factors(causes)

    top_risks = [
        item.title
        for item in ranked
        if item.severity in {CauseSeverity.high, CauseSeverity.critical}
    ][:3]
    data_quality_issues = [item.title for item in ranked if item.cause_category == CauseCategory.data_quality][:3]

    quick_fixes: list[str] = []
    long_term: list[str] = []
    for item in ranked:
        custom_fixes = item.metadata.custom.get("quick_fixes")
        if isinstance(custom_fixes, list):
            quick_fixes.extend(str(fix) for fix in custom_fixes if fix)
        for limitation in item.limitations:
            text = str(limitation).lower()
            if "data" in text or "missing" in text or "quality" in text:
                quick_fixes.append(str(limitation))
            else:
                long_term.append(str(limitation))
        for assumption in item.assumptions:
            long_term.append(str(assumption))

    return CauseSummary(
        top_cause=primary.title if primary else (ranked[0].title if ranked else ""),
        top_risks=top_risks,
        contributing_factors=[item.title for item in contributing[:5]],
        quick_fixes=list(dict.fromkeys(quick_fixes))[:5],
        long_term_improvements=list(dict.fromkeys(long_term))[:5],
        data_quality_issues=data_quality_issues,
        primary_cause_id=primary.root_cause_id if primary else None,
        total_causes=len(causes),
        identified_count=sum(1 for item in causes if item.status == CauseStatus.identified),
        inconclusive_count=sum(1 for item in causes if item.status == CauseStatus.inconclusive),
        blocked_count=sum(1 for item in causes if item.status == CauseStatus.blocked),
    )


def build_root_cause_collection(
    insights: list[UniversalAIInsight] | None = None,
    decisions: list[DecisionRecommendation] | None = None,
    *,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> RootCauseCollection:
    """Build ranked RCA collection from validated insights and optional decisions."""
    insights = insights or []
    decisions = decisions or []
    decision_by_insight = {item.source_insight_id: item for item in decisions if item.source_insight_id}

    causes: list[RootCause] = []
    chains: list[CauseChain] = []

    for insight in insights:
        if insight.validation_status == ValidationStatus.pending:
            continue
        decision = decision_by_insight.get(insight.id)
        cause = build_root_cause(insight=insight, decision=decision)
        chain = build_cause_chain(insight, decision, root_cause_id=cause.root_cause_id)
        causes.append(cause)
        chains.append(chain)

    used_insight_ids = {insight.id for insight in insights}
    for decision in decisions:
        if decision.source_insight_id and decision.source_insight_id in used_insight_ids:
            continue
        if decision.status == DecisionStatus.blocked:
            cause = build_root_cause(decision=decision)
            chain = build_cause_chain(decision=decision, root_cause_id=cause.root_cause_id)
            causes.append(cause)
            chains.append(chain)
            continue
        # Decision-only path when no matching insight was provided.
        if not decision.source_insight_id:
            cause = build_root_cause(decision=decision)
            chain = build_cause_chain(decision=decision, root_cause_id=cause.root_cause_id)
            causes.append(cause)
            chains.append(chain)

    ranked = rank_root_causes(causes)
    ranked_ids = {item.root_cause_id: item for item in ranked}
    ordered_chains = []
    for cause in ranked:
        match = next((chain for chain in chains if cause.root_cause_id in chain.chain_id or chain.chain_id.endswith(cause.root_cause_id)), None)
        if match is None:
            match = next((chain for chain in chains if cause.source_insight_id and cause.source_insight_id in chain.chain_id), None)
        if match is not None:
            ordered_chains.append(match)

    resolved_domain = domain or next((item.domain for item in insights if item.domain), None)
    return RootCauseCollection(
        dataset_id=dataset_id,
        domain=resolved_domain,
        root_causes=ranked,
        chains=ordered_chains,
        summary=summarize_root_causes(ranked),
        generated_at=utc_now_iso(),
        metadata=CauseMetadata(
            legacy={"schema": RCA_SCHEMA_VERSION},
            debug={"cause_count": len(ranked), "ranked_ids": list(ranked_ids.keys())},
            custom={},
            future_extensions={
                "prediction": {},
                "simulation": {},
                "workflow": {},
                "approval": {},
                "automation": {},
            },
        ),
    )
