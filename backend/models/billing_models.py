from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

BILLING_SCHEMA_VERSION = "1.0.0"


class BillingPeriod(str, Enum):
    monthly = "monthly"
    annual = "annual"


class UsageMetric(str, Enum):
    ai_requests = "ai_requests"
    tokens = "tokens"
    workflow_executions = "workflow_executions"
    storage_bytes = "storage_bytes"
    datasets = "datasets"
    knowledge_ingestion = "knowledge_ingestion"
    evaluation_runs = "evaluation_runs"
    api_requests = "api_requests"
    background_jobs = "background_jobs"
    exports = "exports"


class SubscriptionStatus(str, Enum):
    active = "active"
    trialing = "trialing"
    suspended = "suspended"
    cancelled = "cancelled"
    past_due = "past_due"


class InvoiceStatus(str, Enum):
    draft = "draft"
    open = "open"
    paid = "paid"
    void = "void"
    overdue = "overdue"


class PaymentAttemptStatus(str, Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"


class PlanFeature(BaseModel):
    model_config = ConfigDict(extra="allow")

    feature_key: str
    enabled: bool = True
    description: str = ""


class FeatureLimit(BaseModel):
    model_config = ConfigDict(extra="allow")

    metric: UsageMetric | str
    limit_value: int = 0  # 0 = unlimited
    soft_limit: int | None = None
    overage_allowed: bool = False


class SubscriptionPlan(BaseModel):
    model_config = ConfigDict(extra="allow")

    plan_id: str
    name: str
    description: str = ""
    billing_period: BillingPeriod = BillingPeriod.monthly
    price_cents: int = 0
    currency: str = "USD"
    trial_days: int = 0
    features: list[PlanFeature] = Field(default_factory=list)
    limits: list[FeatureLimit] = Field(default_factory=list)
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class Subscription(BaseModel):
    model_config = ConfigDict(extra="allow")

    subscription_id: str
    organization_id: str
    plan_id: str
    status: SubscriptionStatus = SubscriptionStatus.active
    workspace_id: str = ""
    current_period_start: str = ""
    current_period_end: str = ""
    trial_end: str = ""
    cancelled_at: str = ""
    suspended_at: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    record_id: str
    organization_id: str
    workspace_id: str = ""
    user_id: str = ""
    metric: UsageMetric | str
    quantity: float = 0.0
    unit: str = "count"
    recorded_at: str = ""
    billing_period_start: str = ""
    billing_period_end: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class InvoiceItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    item_id: str
    description: str = ""
    metric: str = ""
    quantity: float = 0.0
    unit_price_cents: int = 0
    amount_cents: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Invoice(BaseModel):
    model_config = ConfigDict(extra="allow")

    invoice_id: str
    organization_id: str
    subscription_id: str = ""
    status: InvoiceStatus = InvoiceStatus.draft
    period_start: str = ""
    period_end: str = ""
    subtotal_cents: int = 0
    credit_applied_cents: int = 0
    total_cents: int = 0
    currency: str = "USD"
    items: list[InvoiceItem] = Field(default_factory=list)
    issued_at: str = ""
    due_at: str = ""
    paid_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaymentAttempt(BaseModel):
    model_config = ConfigDict(extra="allow")

    attempt_id: str
    invoice_id: str
    organization_id: str
    amount_cents: int = 0
    status: PaymentAttemptStatus = PaymentAttemptStatus.pending
    provider: str = "internal"
    created_at: str = ""
    completed_at: str = ""
    error_message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreditBalance(BaseModel):
    model_config = ConfigDict(extra="allow")

    balance_id: str
    organization_id: str
    balance_cents: int = 0
    currency: str = "USD"
    updated_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
