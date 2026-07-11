from __future__ import annotations

"""Subscription engine (Sprint 8.6)."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.billing_models import (
    BillingPeriod,
    FeatureLimit,
    PlanFeature,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    UsageMetric,
)

DEFAULT_PLANS: list[SubscriptionPlan] = [
    SubscriptionPlan(
        plan_id="free",
        name="Free",
        description="Starter tier for evaluation",
        price_cents=0,
        trial_days=0,
        features=[
            PlanFeature(feature_key="ai_analyst", enabled=True),
            PlanFeature(feature_key="workflows", enabled=True),
            PlanFeature(feature_key="knowledge", enabled=False),
        ],
        limits=[
            FeatureLimit(metric=UsageMetric.ai_requests, limit_value=100),
            FeatureLimit(metric=UsageMetric.workflow_executions, limit_value=20),
            FeatureLimit(metric=UsageMetric.storage_bytes, limit_value=100 * 1024 * 1024),
            FeatureLimit(metric=UsageMetric.datasets, limit_value=3),
        ],
    ),
    SubscriptionPlan(
        plan_id="pro",
        name="Pro",
        description="Production team tier",
        price_cents=4900,
        trial_days=14,
        features=[
            PlanFeature(feature_key="ai_analyst", enabled=True),
            PlanFeature(feature_key="workflows", enabled=True),
            PlanFeature(feature_key="knowledge", enabled=True),
            PlanFeature(feature_key="evaluation", enabled=True),
        ],
        limits=[
            FeatureLimit(metric=UsageMetric.ai_requests, limit_value=5000),
            FeatureLimit(metric=UsageMetric.workflow_executions, limit_value=500),
            FeatureLimit(metric=UsageMetric.storage_bytes, limit_value=10 * 1024 * 1024 * 1024),
            FeatureLimit(metric=UsageMetric.datasets, limit_value=50),
        ],
    ),
    SubscriptionPlan(
        plan_id="enterprise",
        name="Enterprise",
        description="Unlimited scale with priority support",
        price_cents=19900,
        trial_days=30,
        features=[
            PlanFeature(feature_key="ai_analyst", enabled=True),
            PlanFeature(feature_key="workflows", enabled=True),
            PlanFeature(feature_key="knowledge", enabled=True),
            PlanFeature(feature_key="evaluation", enabled=True),
            PlanFeature(feature_key="admin_portal", enabled=True),
        ],
        limits=[
            FeatureLimit(metric=UsageMetric.ai_requests, limit_value=0),
            FeatureLimit(metric=UsageMetric.workflow_executions, limit_value=0),
            FeatureLimit(metric=UsageMetric.storage_bytes, limit_value=0),
            FeatureLimit(metric=UsageMetric.datasets, limit_value=0),
        ],
    ),
]


class SubscriptionError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


_PLANS: dict[str, SubscriptionPlan] = {p.plan_id: p.model_copy(deep=True) for p in DEFAULT_PLANS}


def _subs():
    from backend.repositories.commercial_registry import get_commercial_stores

    return get_commercial_stores().subscriptions


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat().replace("+00:00", "Z")


def _uid() -> str:
    return f"sub_{uuid.uuid4().hex[:12]}"


def reset_subscriptions() -> None:
    global _PLANS
    _PLANS = {p.plan_id: p.model_copy(deep=True) for p in DEFAULT_PLANS}
    _subs().clear()


def list_plans(*, active_only: bool = True) -> list[SubscriptionPlan]:
    plans = list(_PLANS.values())
    if active_only:
        plans = [p for p in plans if p.is_active]
    return [p.model_copy(deep=True) for p in plans]


def get_plan(plan_id: str) -> SubscriptionPlan | None:
    plan = _PLANS.get(plan_id)
    return plan.model_copy(deep=True) if plan else None


def assign_plan(
    organization_id: str,
    plan_id: str,
    *,
    workspace_id: str = "",
    start_trial: bool = False,
) -> Subscription:
    plan = get_plan(plan_id)
    if plan is None:
        raise SubscriptionError(f"Plan not found: {plan_id}", status_code=404)

    existing = get_subscription(organization_id)
    if existing:
        return upgrade_plan(organization_id, plan_id, start_trial=start_trial)

    now = _now()
    period_end = now + timedelta(days=30 if plan.billing_period == BillingPeriod.monthly else 365)
    status = SubscriptionStatus.trialing if start_trial and plan.trial_days else SubscriptionStatus.active
    trial_end = ""
    if status == SubscriptionStatus.trialing:
        trial_end = (now + timedelta(days=plan.trial_days)).isoformat().replace("+00:00", "Z")

    sub = Subscription(
        subscription_id=_uid(),
        organization_id=organization_id,
        workspace_id=workspace_id,
        plan_id=plan_id,
        status=status,
        current_period_start=now.isoformat().replace("+00:00", "Z"),
        current_period_end=period_end.isoformat().replace("+00:00", "Z"),
        trial_end=trial_end,
        created_at=_now_iso(),
        updated_at=_now_iso(),
    )
    _subs().save(sub)
    return sub.model_copy(deep=True)


def get_subscription(organization_id: str) -> Subscription | None:
    return _subs().get(organization_id)


def upgrade_plan(organization_id: str, new_plan_id: str, *, start_trial: bool = False) -> Subscription:
    sub = get_subscription(organization_id)
    if sub is None:
        return assign_plan(organization_id, new_plan_id, start_trial=start_trial)
    plan = get_plan(new_plan_id)
    if plan is None:
        raise SubscriptionError(f"Plan not found: {new_plan_id}", status_code=404)
    sub.plan_id = new_plan_id
    sub.updated_at = _now_iso()
    if start_trial and plan.trial_days:
        sub.status = SubscriptionStatus.trialing
        sub.trial_end = (_now() + timedelta(days=plan.trial_days)).isoformat().replace("+00:00", "Z")
    elif sub.status == SubscriptionStatus.suspended:
        sub.status = SubscriptionStatus.active
    _subs().save(sub)
    return sub.model_copy(deep=True)


def downgrade_plan(organization_id: str, new_plan_id: str) -> Subscription:
    return upgrade_plan(organization_id, new_plan_id)


def suspend_subscription(organization_id: str, *, reason: str = "") -> Subscription:
    sub = get_subscription(organization_id)
    if sub is None:
        raise SubscriptionError("No subscription found", status_code=404)
    sub.status = SubscriptionStatus.suspended
    sub.suspended_at = _now_iso()
    sub.metadata = {**sub.metadata, "suspend_reason": reason}
    sub.updated_at = _now_iso()
    _subs().save(sub)
    return sub.model_copy(deep=True)


def reactivate_subscription(organization_id: str) -> Subscription:
    sub = get_subscription(organization_id)
    if sub is None:
        raise SubscriptionError("No subscription found", status_code=404)
    sub.status = SubscriptionStatus.active
    sub.suspended_at = ""
    sub.updated_at = _now_iso()
    _subs().save(sub)
    return sub.model_copy(deep=True)


def cancel_subscription(organization_id: str) -> Subscription:
    sub = get_subscription(organization_id)
    if sub is None:
        raise SubscriptionError("No subscription found", status_code=404)
    sub.status = SubscriptionStatus.cancelled
    sub.cancelled_at = _now_iso()
    sub.updated_at = _now_iso()
    _subs().save(sub)
    return sub.model_copy(deep=True)


def feature_available(organization_id: str, feature_key: str) -> bool:
    sub = get_subscription(organization_id)
    if sub is None or sub.status == SubscriptionStatus.suspended:
        return feature_key in {"ai_analyst"}
    if sub.status not in {SubscriptionStatus.active, SubscriptionStatus.trialing}:
        return False
    plan = get_plan(sub.plan_id)
    if plan is None:
        return False
    for feat in plan.features:
        if feat.feature_key == feature_key:
            return feat.enabled
    return False


def get_limits(organization_id: str) -> list[FeatureLimit]:
    sub = get_subscription(organization_id)
    if sub is None:
        plan = get_plan("free")
        return list(plan.limits) if plan else []
    plan = get_plan(sub.plan_id)
    return list(plan.limits) if plan else []


def check_quota(organization_id: str, metric: UsageMetric | str, *, additional: float = 0.0) -> dict[str, Any]:
    """Evaluate quota for a metric. Raises SubscriptionError when hard limit exceeded."""
    from backend.services.usage_service import aggregate_usage

    mkey = metric.value if hasattr(metric, "value") else str(metric)
    sub = get_subscription(organization_id)
    if sub and sub.status == SubscriptionStatus.suspended:
        raise SubscriptionError("Subscription suspended", status_code=403)

    limits = get_limits(organization_id)
    limit = next((l for l in limits if (l.metric.value if hasattr(l.metric, "value") else str(l.metric)) == mkey), None)
    if limit is None or limit.limit_value == 0:
        return {"allowed": True, "metric": mkey, "limit": 0, "used": 0, "unlimited": True}

    used = aggregate_usage(organization_id=organization_id).get(mkey, 0.0)
    projected = used + additional
    allowed = projected <= limit.limit_value
    if not allowed and not limit.overage_allowed:
        raise SubscriptionError(f"Quota exceeded for {mkey} ({projected:.0f}/{limit.limit_value})", status_code=429)
    return {
        "allowed": allowed,
        "metric": mkey,
        "limit": limit.limit_value,
        "used": used,
        "projected": projected,
        "unlimited": False,
    }


def enforce_limit(organization_id: str, metric: UsageMetric | str) -> None:
    check_quota(organization_id, metric, additional=1.0)
