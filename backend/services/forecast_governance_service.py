from __future__ import annotations

from typing import Any

from backend.models.ai_insight_models import utc_now_iso
from backend.models.forecast_governance_models import (
    FORECAST_GOVERNANCE_SCHEMA_VERSION,
    ApprovalStatus,
    ComplianceStatus,
    ForecastAuditRecord,
    ForecastGovernance,
    GovernanceMetadata,
    GovernanceStatistics,
    GovernanceSummary,
    LifecycleStatus,
    empty_forecast_governance_future_extensions,
)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _parse_lifecycle(raw: Any) -> LifecycleStatus:
    if isinstance(raw, LifecycleStatus):
        return raw
    if raw is None or raw == "":
        return LifecycleStatus.draft
    return LifecycleStatus(str(raw).strip().lower())


def _parse_approval(raw: Any) -> ApprovalStatus:
    if isinstance(raw, ApprovalStatus):
        return raw
    if raw is None or raw == "":
        return ApprovalStatus.pending
    return ApprovalStatus(str(raw).strip().lower())


def _parse_compliance(raw: Any) -> ComplianceStatus:
    if isinstance(raw, ComplianceStatus):
        return raw
    if raw is None or raw == "":
        return ComplianceStatus.unknown
    return ComplianceStatus(str(raw).strip().lower())


def _normalize_metadata(
    metadata: dict[str, Any] | GovernanceMetadata | None,
) -> GovernanceMetadata:
    if isinstance(metadata, GovernanceMetadata):
        meta = metadata.model_copy(deep=True)
        if not meta.future_extensions:
            meta.future_extensions = empty_forecast_governance_future_extensions()
        return meta
    meta_dict = dict(metadata or {})
    future = meta_dict.get("future_extensions")
    if not isinstance(future, dict) or not future:
        future = empty_forecast_governance_future_extensions()
    return GovernanceMetadata(
        legacy=dict(meta_dict.get("legacy", {})),
        debug=dict(meta_dict.get("debug", {})),
        custom=dict(meta_dict.get("custom", {})),
        future_extensions=future,
    )


def build_default_governance(
    *,
    forecast_id: str | None = None,
    dataset_id: str | None = None,
    owner: str = "",
) -> ForecastGovernance:
    """Build a template governance record. Metadata only — no approval workflow."""
    return build_governance(
        forecast_id=forecast_id,
        dataset_id=dataset_id,
        owner=owner or "unassigned",
        business_unit="",
        forecast_version="0.0.0",
        lifecycle_status=LifecycleStatus.draft,
        approval_status=ApprovalStatus.pending,
        compliance_status=ComplianceStatus.unknown,
        review_frequency="",
        retention_policy="",
        tags=[],
    )


def build_governance(
    *,
    forecast_id: str | None = None,
    dataset_id: str | None = None,
    owner: str = "",
    business_unit: str = "",
    forecast_version: str = "0.0.0",
    lifecycle_status: LifecycleStatus | str = LifecycleStatus.draft,
    approval_status: ApprovalStatus | str = ApprovalStatus.pending,
    compliance_status: ComplianceStatus | str = ComplianceStatus.unknown,
    review_frequency: str = "",
    last_reviewed_at: str = "",
    next_review_at: str = "",
    retention_policy: str = "",
    audit_reference: str = "",
    tags: list[str] | None = None,
    audit_records: list[ForecastAuditRecord] | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
    metadata: dict[str, Any] | GovernanceMetadata | None = None,
    governance_id: str | None = None,
) -> ForecastGovernance:
    """Construct ForecastGovernance from caller-supplied metadata. Never approves or enforces."""
    now = utc_now_iso()
    stamp = (created_at or now).replace(":", "").replace("-", "")
    tag_list = _unique(list(tags or []))
    records = [r.model_copy(deep=True) for r in (audit_records or [])]
    meta = _normalize_metadata(metadata)
    meta.debug = {
        **meta.debug,
        "audit_record_count": len(records),
        "schema": FORECAST_GOVERNANCE_SCHEMA_VERSION,
    }
    meta.legacy = {**meta.legacy, "schema": FORECAST_GOVERNANCE_SCHEMA_VERSION}

    resolved_id = (
        f"forecast_governance_{stamp}" if governance_id is None else governance_id
    )
    return ForecastGovernance(
        governance_id=resolved_id,
        forecast_id=forecast_id,
        dataset_id=dataset_id,
        owner=owner,
        business_unit=business_unit,
        forecast_version=forecast_version,
        lifecycle_status=_parse_lifecycle(lifecycle_status),
        approval_status=_parse_approval(approval_status),
        compliance_status=_parse_compliance(compliance_status),
        review_frequency=review_frequency,
        last_reviewed_at=last_reviewed_at,
        next_review_at=next_review_at,
        retention_policy=retention_policy,
        audit_reference=audit_reference,
        tags=tag_list,
        audit_records=records,
        created_at=created_at or now,
        updated_at=updated_at or now,
        metadata=meta,
        schema_version=FORECAST_GOVERNANCE_SCHEMA_VERSION,
    )


def register_audit_record(
    governance: ForecastGovernance,
    record: ForecastAuditRecord,
    *,
    replace: bool = True,
) -> ForecastGovernance:
    """Append or replace one audit record. Does not mutate the input object."""
    copy = governance.model_copy(deep=True)
    item = record.model_copy(deep=True)
    if not item.timestamp:
        item.timestamp = utc_now_iso()
    if not item.reference_id:
        item.reference_id = copy.governance_id
    records = list(copy.audit_records)
    existing_idx = next(
        (i for i, r in enumerate(records) if r.audit_id == item.audit_id),
        None,
    )
    if existing_idx is None:
        records.append(item)
    elif replace:
        records[existing_idx] = item
    else:
        return copy
    copy.audit_records = records
    copy.updated_at = utc_now_iso()
    if not copy.audit_reference:
        copy.audit_reference = item.audit_id
    copy.metadata.debug = {
        **copy.metadata.debug,
        "audit_record_count": len(records),
    }
    return copy


def find_audit_record(
    governance: ForecastGovernance,
    audit_id: str,
) -> ForecastAuditRecord | None:
    for item in governance.audit_records:
        if item.audit_id == audit_id:
            return item.model_copy(deep=True)
    return None


def list_audit_records(
    governance: ForecastGovernance,
    *,
    event_type: str | None = None,
) -> list[ForecastAuditRecord]:
    results: list[ForecastAuditRecord] = []
    for item in governance.audit_records:
        if event_type is not None and item.event_type != event_type:
            continue
        results.append(item.model_copy(deep=True))
    return results


def governance_statistics(governance: ForecastGovernance) -> GovernanceStatistics:
    pending = approved = rejected = 0
    # Count approval-related events from audit records; status counts from current state.
    approval_event_count = 0
    for record in governance.audit_records:
        if "approval" in (record.event_type or "").lower():
            approval_event_count += 1

    if governance.approval_status == ApprovalStatus.pending:
        pending = 1
    elif governance.approval_status == ApprovalStatus.approved:
        approved = 1
    elif governance.approval_status == ApprovalStatus.rejected:
        rejected = 1

    compliance_summary = {
        status.value: 0 for status in ComplianceStatus
    }
    compliance_summary[governance.compliance_status.value] = 1

    return GovernanceStatistics(
        audit_record_count=len(governance.audit_records),
        approval_count=approval_event_count,
        pending_count=pending,
        approved_count=approved,
        rejected_count=rejected,
        compliance_summary=compliance_summary,
        tag_count=len(governance.tags),
    )


def governance_summary(governance: ForecastGovernance) -> GovernanceSummary:
    parts: list[str] = []
    if governance.review_frequency:
        parts.append(f"frequency={governance.review_frequency}")
    if governance.last_reviewed_at:
        parts.append(f"last={governance.last_reviewed_at}")
    if governance.next_review_at:
        parts.append(f"next={governance.next_review_at}")
    review_schedule = "; ".join(parts) if parts else "unset"
    return GovernanceSummary(
        forecast_version=governance.forecast_version,
        owner=governance.owner,
        business_unit=governance.business_unit,
        lifecycle_status=governance.lifecycle_status.value,
        approval_status=governance.approval_status.value,
        compliance_status=governance.compliance_status.value,
        audit_records=len(governance.audit_records),
        review_schedule=review_schedule,
    )


def validate_governance(
    governance: ForecastGovernance,
    *,
    known_governance_ids: set[str] | None = None,
) -> dict[str, object]:
    """Structural integrity only — never approves, rejects, or enforces policy."""
    issues: list[str] = []
    seen_audit_ids: set[str] = set()

    if not governance.governance_id and not governance.forecast_id and not governance.owner:
        issues.append("Empty governance object")

    if not governance.governance_id:
        issues.append("Missing governance_id")
    elif known_governance_ids and governance.governance_id in known_governance_ids:
        issues.append(f"Duplicate governance_id: {governance.governance_id}")

    if not governance.forecast_id:
        issues.append("Missing forecast id")
    if not str(governance.owner or "").strip():
        issues.append("Missing owner")

    try:
        if governance.lifecycle_status not in LifecycleStatus:
            issues.append(f"Invalid lifecycle status: {governance.lifecycle_status}")
    except Exception:
        issues.append(f"Invalid lifecycle status: {governance.lifecycle_status}")

    try:
        if governance.approval_status not in ApprovalStatus:
            issues.append(f"Invalid approval status: {governance.approval_status}")
    except Exception:
        issues.append(f"Invalid approval status: {governance.approval_status}")

    try:
        if governance.compliance_status not in ComplianceStatus:
            issues.append(f"Invalid compliance status: {governance.compliance_status}")
    except Exception:
        issues.append(f"Invalid compliance status: {governance.compliance_status}")

    for record in governance.audit_records:
        if not record.audit_id:
            issues.append("Audit record missing audit_id")
            continue
        if record.audit_id in seen_audit_ids:
            issues.append(f"Duplicate audit id: {record.audit_id}")
        seen_audit_ids.add(record.audit_id)

    required_extensions = set(empty_forecast_governance_future_extensions().keys())
    missing_extensions = sorted(
        required_extensions - set(governance.metadata.future_extensions.keys())
    )
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "governance_id": governance.governance_id,
        "audit_record_count": len(governance.audit_records),
    }
