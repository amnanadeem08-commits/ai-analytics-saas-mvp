from __future__ import annotations

from backend.models.billing_models import UsageMetric
from backend.services import usage_service


def setup_function():
    usage_service.reset_usage()
    from backend.services.subscription_service import reset_subscriptions

    reset_subscriptions()


def test_usage_aggregation():
    usage_service.record_usage(UsageMetric.api_requests, 5, organization_id="org_u", user_id="u1")
    usage_service.record_usage(UsageMetric.workflow_executions, 2, organization_id="org_u", workspace_id="ws1")
    totals = usage_service.aggregate_usage(organization_id="org_u")
    assert totals["api_requests"] == 5
    assert totals["workflow_executions"] == 2


def test_usage_summary():
    usage_service.record_usage(UsageMetric.datasets, 1, organization_id="org_u2")
    summary = usage_service.usage_summary("org_u2")
    assert summary["record_count"] == 1
