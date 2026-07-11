from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from unittest.mock import patch

import pytest

from backend.services import billing_service, subscription_service, usage_service
from backend.services.billing_service import BillingError
from backend.services.payment_gateway import (
    reset_payment_gateway,
    reset_payment_gateway_config,
)
from backend.services.payment_gateway.stripe_gateway import StripePaymentGateway


ORG = "org_gateway_test"


def setup_function():
    usage_service.reset_usage()
    subscription_service.reset_subscriptions()
    billing_service.reset_billing()
    reset_payment_gateway()
    reset_payment_gateway_config()
    os.environ.pop("BILLING_GATEWAY", None)
    os.environ.pop("STRIPE_SECRET_KEY", None)
    os.environ.pop("STRIPE_WEBHOOK_SECRET", None)


def test_gateway_status_defaults_to_internal():
    status = billing_service.get_gateway_status()
    assert status["configured_provider"] == "internal"
    assert status["active_provider"] == "internal"
    assert status["ready"] is True
    assert status["is_live"] is False


def test_internal_checkout_marks_invoice_paid():
    subscription_service.assign_plan(ORG, "pro")
    invoice = billing_service.generate_invoice(ORG)
    assert invoice.status.value == "open"

    session = billing_service.start_checkout(invoice.invoice_id)
    assert session.provider == "internal"
    assert session.status == "succeeded"

    paid = billing_service.get_invoice(invoice.invoice_id)
    assert paid is not None
    assert paid.status.value == "paid"
    assert paid.metadata.get("payment_provider") == "internal"


def test_record_payment_attempt_still_succeeds_via_gateway():
    subscription_service.assign_plan(ORG, "pro")
    invoice = billing_service.generate_invoice(ORG)
    payment = billing_service.record_payment_attempt(invoice.invoice_id)
    assert payment.status.value == "succeeded"
    assert payment.provider == "internal"
    assert billing_service.get_invoice(invoice.invoice_id).status.value == "paid"


def test_stripe_gateway_requires_secret_key():
    os.environ["BILLING_GATEWAY"] = "stripe"
    reset_payment_gateway()
    reset_payment_gateway_config()
    status = billing_service.get_gateway_status()
    assert status["ready"] is False
    assert "STRIPE_SECRET_KEY" in status["error"]


def test_stripe_checkout_uses_http_api(monkeypatch):
    os.environ["BILLING_GATEWAY"] = "stripe"
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_dummy"
    reset_payment_gateway()
    reset_payment_gateway_config()

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {
                "id": "cs_test_123",
                "url": "https://checkout.stripe.com/c/pay/cs_test_123",
                "status": "open",
                "payment_status": "unpaid",
            }

        text = ""

    with patch("backend.services.payment_gateway.stripe_gateway.requests.post", return_value=_Resp()) as mocked:
        subscription_service.assign_plan(ORG, "pro")
        invoice = billing_service.generate_invoice(ORG)
        session = billing_service.start_checkout(invoice.invoice_id)
        assert session.provider == "stripe"
        assert session.status == "open"
        assert session.checkout_url.startswith("https://checkout.stripe.com/")
        assert mocked.called
        # Invoice remains open until webhook
        assert billing_service.get_invoice(invoice.invoice_id).status.value == "open"


def test_stripe_webhook_marks_paid():
    secret = "whsec_test_secret"
    os.environ["STRIPE_WEBHOOK_SECRET"] = secret
    reset_payment_gateway_config()

    subscription_service.assign_plan(ORG, "pro")
    invoice = billing_service.generate_invoice(ORG)

    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_wh",
                "client_reference_id": invoice.invoice_id,
                "amount_total": invoice.total_cents,
                "payment_status": "paid",
                "status": "complete",
                "metadata": {"invoice_id": invoice.invoice_id},
            }
        },
    }
    body = json.dumps(payload).encode("utf-8")
    timestamp = str(int(time.time()))
    signed = f"{timestamp}.".encode("utf-8") + body
    sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    headers = {"stripe-signature": f"t={timestamp},v1={sig}"}

    result = billing_service.handle_payment_webhook(provider="stripe", headers=headers, body=body)
    assert result["handled"] is True
    assert billing_service.get_invoice(invoice.invoice_id).status.value == "paid"


def test_stripe_webhook_rejects_bad_signature():
    os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"
    reset_payment_gateway_config()
    body = b'{"type":"checkout.session.completed","data":{"object":{}}}'
    with pytest.raises(BillingError):
        billing_service.handle_payment_webhook(
            provider="stripe",
            headers={"stripe-signature": "t=1,v1=deadbeef"},
            body=body,
        )


def test_checkout_rejects_already_paid_invoice():
    subscription_service.assign_plan(ORG, "pro")
    invoice = billing_service.generate_invoice(ORG)
    billing_service.start_checkout(invoice.invoice_id)
    with pytest.raises(BillingError):
        billing_service.start_checkout(invoice.invoice_id)
