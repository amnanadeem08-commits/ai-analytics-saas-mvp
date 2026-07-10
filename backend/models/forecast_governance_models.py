from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

FORECAST_GOVERNANCE_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future governance engines. Placeholders only.
FORECAST_GOVERNANCE_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "rbac",
    "approval_workflow",
    "electronic_signatures",
    "policy_engine",
    "lineage",
    "data_catalog",
    "governance_dashboard",
    "compliance_engine",
    "risk_register",
    "security",
    "privacy",
    "access_control",
)


def empty_forecast_governance_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in FORECAST_GOVERNANCE_FUTURE_EXTENSION_KEYS}


class LifecycleStatus(str, Enum):
    draft = "draft"
    review = "review"
    approved = "approved"
    published = "published"
    archived = "archived"
    retired = "retired"


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    not_required = "not_required"


class ComplianceStatus(str, Enum):
    unknown = "unknown"
    compliant = "compliant"
    warning = "warning"
    non_compliant = "non_compliant"


class ForecastAuditRecord(BaseModel):
    """One governance audit event. Metadata only — never executes approvals."""

    model_config = ConfigDict(extra="allow")

    audit_id: str
    event_type: str = ""
    actor: str = ""
    timestamp: str = ""
    reference_id: str | None = None
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_forecast_governance_future_extensions
    )


class GovernanceStatistics(BaseModel):
    audit_record_count: int = 0
    approval_count: int = 0
    pending_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    compliance_summary: dict[str, int] = Field(default_factory=dict)
    tag_count: int = 0


class GovernanceSummary(BaseModel):
    forecast_version: str = ""
    owner: str = ""
    business_unit: str = ""
    lifecycle_status: str = ""
    approval_status: str = ""
    compliance_status: str = ""
    audit_records: int = 0
    review_schedule: str = ""


class ForecastGovernance(BaseModel):
    """Canonical forecast governance object. Metadata only — never enforces policy."""

    model_config = ConfigDict(extra="allow")

    governance_id: str
    forecast_id: str | None = None
    dataset_id: str | None = None
    owner: str = ""
    business_unit: str = ""
    forecast_version: str = ""
    lifecycle_status: LifecycleStatus = LifecycleStatus.draft
    approval_status: ApprovalStatus = ApprovalStatus.pending
    compliance_status: ComplianceStatus = ComplianceStatus.unknown
    review_frequency: str = ""
    last_reviewed_at: str = ""
    next_review_at: str = ""
    retention_policy: str = ""
    audit_reference: str = ""
    tags: list[str] = Field(default_factory=list)
    audit_records: list[ForecastAuditRecord] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    metadata: GovernanceMetadata = Field(default_factory=GovernanceMetadata)
    schema_version: str = FORECAST_GOVERNANCE_SCHEMA_VERSION
