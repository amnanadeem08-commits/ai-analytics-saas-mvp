from __future__ import annotations

import pytest

from backend.models.billing_models import UsageMetric
from backend.services import billing_service, subscription_service, usage_service
from backend.services.billing_service import BillingError
from backend.services.subscription_service import SubscriptionError


ORG = "org_billing_test"


def setup_function():
    usage_service.reset_usage()
    subscription_service.reset_subscriptions()
    billing_service.reset_billing()


def test_assign_and_upgrade_subscription():
    sub = subscription_service.assign_plan(ORG, "free")
    assert sub.plan_id == "free"
    upgraded = subscription_service.upgrade_plan(ORG, "pro", start_trial=True)
    assert upgraded.plan_id == "pro"
    assert upgraded.status.value == "trialing"


def test_suspend_and_reactivate():
    subscription_service.assign_plan(ORG, "pro")
    suspended = subscription_service.suspend_subscription(ORG)
    assert suspended.status.value == "suspended"
    reactivated = subscription_service.reactivate_subscription(ORG)
    assert reactivated.status.value == "active"


def test_quota_enforcement():
    subscription_service.assign_plan(ORG, "free")
    for _ in range(100):
        usage_service.record_usage(UsageMetric.ai_requests, 1, organization_id=ORG)
    with pytest.raises(SubscriptionError):
        usage_service.record_usage(UsageMetric.ai_requests, 1, organization_id=ORG)


def test_feature_availability():
    subscription_service.assign_plan(ORG, "free")
    assert subscription_service.feature_available(ORG, "ai_analyst") is True
    assert subscription_service.feature_available(ORG, "knowledge") is False


def test_estimated_charges_and_invoice():
    subscription_service.assign_plan(ORG, "pro")
    usage_service.record_usage(UsageMetric.ai_requests, 10, organization_id=ORG)
    estimate = billing_service.estimated_charges(ORG)
    assert estimate["base_cents"] == 4900
    invoice = billing_service.generate_invoice(ORG)
    assert invoice.total_cents >= 0
    assert invoice.status.value == "open"
    payment = billing_service.record_payment_attempt(invoice.invoice_id)
    assert payment.status.value == "succeeded"
    paid = billing_service.get_invoice(invoice.invoice_id)
    assert paid.status.value == "paid"


def test_credit_balance():
    billing_service.add_credit(ORG, 500)
    bal = billing_service.get_credit_balance(ORG)
    assert bal.balance_cents == 500
