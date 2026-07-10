from __future__ import annotations

from backend.models.forecast_governance_models import (
    FORECAST_GOVERNANCE_FUTURE_EXTENSION_KEYS,
    ApprovalStatus,
    ComplianceStatus,
    ForecastAuditRecord,
    LifecycleStatus,
)
from backend.services.forecast_governance_service import (
    build_default_governance,
    build_governance,
    find_audit_record,
    governance_statistics,
    governance_summary,
    list_audit_records,
    register_audit_record,
    validate_governance,
)


def test_governance_creation_and_default():
    governance = build_governance(
        forecast_id="fc_1",
        dataset_id="ds_1",
        owner="analytics_team",
        business_unit="Finance",
        forecast_version="1.2.0",
        lifecycle_status=LifecycleStatus.review,
        approval_status=ApprovalStatus.pending,
        compliance_status=ComplianceStatus.warning,
        review_frequency="quarterly",
        last_reviewed_at="2026-01-01T00:00:00Z",
        next_review_at="2026-04-01T00:00:00Z",
        retention_policy="7y",
        tags=["finance", "baseline"],
    )
    assert governance.forecast_id == "fc_1"
    assert governance.owner == "analytics_team"
    assert governance.lifecycle_status == LifecycleStatus.review
    assert validate_governance(governance)["valid"] is True

    default = build_default_governance(forecast_id="fc_2", dataset_id="ds_2")
    assert default.lifecycle_status == LifecycleStatus.draft
    assert default.approval_status == ApprovalStatus.pending
    assert default.compliance_status == ComplianceStatus.unknown
    assert default.owner == "unassigned"
    assert validate_governance(default)["valid"] is True


def test_audit_registration_and_lookup():
    governance = build_governance(
        forecast_id="fc_1",
        owner="owner_a",
        lifecycle_status="draft",
        approval_status="pending",
    )
    record = ForecastAuditRecord(
        audit_id="aud_1",
        event_type="governance_created",
        actor="system",
        description="Initial governance metadata recorded.",
    )
    updated = register_audit_record(governance, record)
    assert find_audit_record(governance, "aud_1") is None
    assert find_audit_record(updated, "aud_1") is not None
    assert len(list_audit_records(updated)) == 1
    assert len(list_audit_records(updated, event_type="governance_created")) == 1
    assert list_audit_records(updated, event_type="missing") == []

    approval = ForecastAuditRecord(
        audit_id="aud_2",
        event_type="approval_noted",
        actor="reviewer",
        description="Approval status noted in metadata only.",
    )
    with_approval = register_audit_record(updated, approval)
    assert len(with_approval.audit_records) == 2
    assert find_audit_record(with_approval, "aud_2") is not None


def test_statistics_and_summary():
    governance = build_governance(
        forecast_id="fc_1",
        owner="owner_a",
        business_unit="Ops",
        forecast_version="2.0.0",
        lifecycle_status=LifecycleStatus.approved,
        approval_status=ApprovalStatus.approved,
        compliance_status=ComplianceStatus.compliant,
        review_frequency="monthly",
        last_reviewed_at="2026-06-01T00:00:00Z",
        next_review_at="2026-07-01T00:00:00Z",
        tags=["ops", "published"],
    )
    governance = register_audit_record(
        governance,
        ForecastAuditRecord(
            audit_id="aud_a",
            event_type="approval_noted",
            actor="reviewer",
            description="Noted",
        ),
    )
    stats = governance_statistics(governance)
    assert stats.audit_record_count == 1
    assert stats.approval_count == 1
    assert stats.approved_count == 1
    assert stats.pending_count == 0
    assert stats.rejected_count == 0
    assert stats.compliance_summary["compliant"] == 1
    assert stats.tag_count == 2

    summary = governance_summary(governance)
    assert summary.forecast_version == "2.0.0"
    assert summary.owner == "owner_a"
    assert summary.business_unit == "Ops"
    assert summary.lifecycle_status == "approved"
    assert summary.approval_status == "approved"
    assert summary.compliance_status == "compliant"
    assert summary.audit_records == 1
    assert "monthly" in summary.review_schedule
    assert "next=" in summary.review_schedule


def test_validation():
    good = build_governance(forecast_id="fc_1", owner="owner_a")
    assert validate_governance(good)["valid"] is True

    missing_owner = build_governance(forecast_id="fc_1", owner="")
    assert any("Missing owner" in i for i in validate_governance(missing_owner)["issues"])

    missing_forecast = build_governance(forecast_id=None, owner="owner_a")
    assert any(
        "Missing forecast id" in i for i in validate_governance(missing_forecast)["issues"]
    )

    empty = build_governance(
        governance_id="",
        forecast_id=None,
        owner="",
    )
    empty_issues = validate_governance(empty)["issues"]
    assert any("Empty governance object" in i for i in empty_issues)

    dup_gov = validate_governance(good, known_governance_ids={good.governance_id})
    assert any("Duplicate governance_id" in i for i in dup_gov["issues"])

    with_audits = register_audit_record(
        good,
        ForecastAuditRecord(audit_id="dup", event_type="a", actor="x"),
    )
    with_dup = with_audits.model_copy(deep=True)
    with_dup.audit_records = list(with_dup.audit_records) + [
        with_dup.audit_records[0].model_copy(deep=True)
    ]
    assert any(
        "Duplicate audit id" in i for i in validate_governance(with_dup)["issues"]
    )


def test_future_extension_buckets():
    governance = build_default_governance(forecast_id="fc_x")
    for key in FORECAST_GOVERNANCE_FUTURE_EXTENSION_KEYS:
        assert key in governance.metadata.future_extensions
        assert governance.metadata.future_extensions[key] == {}
    assert "rbac" in governance.metadata.future_extensions
    assert "approval_workflow" in governance.metadata.future_extensions
    assert "access_control" in governance.metadata.future_extensions


def test_immutability():
    governance = build_governance(
        forecast_id="fc_1",
        owner="owner_a",
        tags=["t1"],
    )
    with_audit = register_audit_record(
        governance,
        ForecastAuditRecord(
            audit_id="aud_1",
            event_type="note",
            actor="system",
            description="note",
        ),
    )
    snapshot = with_audit.model_dump()
    found = find_audit_record(with_audit, "aud_1")
    assert found is not None
    found.description = "mutated"
    listed = list_audit_records(with_audit)
    listed[0].description = "mutated_list"
    governance_statistics(with_audit)
    governance_summary(with_audit)
    validate_governance(with_audit)
    register_audit_record(
        with_audit,
        ForecastAuditRecord(audit_id="aud_2", event_type="e", actor="a"),
    )
    assert find_audit_record(governance, "aud_1") is None
    assert with_audit.model_dump() == snapshot
