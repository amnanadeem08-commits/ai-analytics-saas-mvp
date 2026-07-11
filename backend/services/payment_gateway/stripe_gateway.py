from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any
from urllib.parse import urlencode

import requests

from backend.services.payment_gateway.config import PaymentGatewayConfig, get_payment_gateway_config
from backend.services.payment_gateway.interfaces import CheckoutSession, WebhookEvent


class StripeGatewayError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class StripePaymentGateway:
    """Stripe Checkout integration via HTTPS (no stripe SDK dependency)."""

    def __init__(self, config: PaymentGatewayConfig | None = None):
        self._config = config or get_payment_gateway_config()

    @property
    def name(self) -> str:
        return "stripe"

    def is_live(self) -> bool:
        return bool(self._config.stripe_secret_key)

    def create_checkout(
        self,
        *,
        invoice_id: str,
        organization_id: str,
        amount_cents: int,
        currency: str,
        success_url: str,
        cancel_url: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CheckoutSession:
        if not self._config.stripe_secret_key:
            raise StripeGatewayError(
                "STRIPE_SECRET_KEY is not configured",
                status_code=503,
            )
        if amount_cents < 0:
            raise StripeGatewayError("amount_cents must be >= 0")

        meta = {
            "invoice_id": invoice_id,
            "organization_id": organization_id,
            **(metadata or {}),
        }
        # Stripe Checkout Session (form-encoded API)
        form: dict[str, Any] = {
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": invoice_id,
            "line_items[0][quantity]": 1,
            "line_items[0][price_data][currency]": currency.lower(),
            "line_items[0][price_data][unit_amount]": max(amount_cents, 0),
            "line_items[0][price_data][product_data][name]": description or f"Invoice {invoice_id}",
        }
        for key, value in meta.items():
            form[f"metadata[{key}]"] = str(value)

        if amount_cents == 0:
            # Stripe rejects zero; treat as internal success session without API call.
            session_id = f"stripe_free_{uuid.uuid4().hex[:12]}"
            return CheckoutSession(
                session_id=session_id,
                provider=self.name,
                invoice_id=invoice_id,
                organization_id=organization_id,
                amount_cents=0,
                currency=currency,
                status="succeeded",
                checkout_url=success_url,
                provider_reference=session_id,
                metadata=meta,
            )

        response = requests.post(
            f"{self._config.stripe_api_base}/v1/checkout/sessions",
            data=urlencode(form),
            headers={
                "Authorization": f"Bearer {self._config.stripe_secret_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )
        if response.status_code >= 400:
            detail = response.text[:500]
            raise StripeGatewayError(
                f"Stripe checkout session failed ({response.status_code}): {detail}",
                status_code=502,
            )
        payload = response.json()
        session_id = str(payload.get("id") or "")
        return CheckoutSession(
            session_id=session_id,
            provider=self.name,
            invoice_id=invoice_id,
            organization_id=organization_id,
            amount_cents=amount_cents,
            currency=currency,
            status=str(payload.get("status") or "open"),
            checkout_url=str(payload.get("url") or ""),
            provider_reference=session_id,
            metadata={**meta, "stripe_payment_status": payload.get("payment_status")},
        )

    def verify_webhook(self, *, headers: dict[str, str], body: bytes) -> WebhookEvent:
        secret = self._config.stripe_webhook_secret
        if not secret:
            raise StripeGatewayError("STRIPE_WEBHOOK_SECRET is not configured", status_code=503)

        signature_header = headers.get("stripe-signature") or headers.get("Stripe-Signature") or ""
        if not signature_header:
            raise StripeGatewayError("Missing Stripe-Signature header", status_code=400)

        self._assert_valid_signature(signature_header, body, secret)

        try:
            event = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StripeGatewayError("Invalid webhook JSON body", status_code=400) from exc

        event_type = str(event.get("type") or "")
        data_object = (event.get("data") or {}).get("object") or {}
        invoice_id = str(
            data_object.get("client_reference_id")
            or (data_object.get("metadata") or {}).get("invoice_id")
            or ""
        )
        amount = int(data_object.get("amount_total") or data_object.get("amount") or 0)
        paid = event_type in {
            "checkout.session.completed",
            "payment_intent.succeeded",
            "invoice.paid",
        } and str(data_object.get("payment_status") or "paid") in {"paid", "complete", ""}

        if event_type == "checkout.session.completed":
            paid = str(data_object.get("payment_status") or "") == "paid" or data_object.get("status") == "complete"
            if data_object.get("payment_status") == "paid":
                paid = True
            # Prefer explicit payment_status
            paid = str(data_object.get("payment_status", "")).lower() == "paid"

        return WebhookEvent(
            event_type=event_type,
            provider=self.name,
            invoice_id=invoice_id,
            provider_reference=str(data_object.get("id") or ""),
            amount_cents=amount,
            paid=paid,
            raw=event if isinstance(event, dict) else {},
        )

    @staticmethod
    def _assert_valid_signature(header: str, body: bytes, secret: str, *, tolerance_sec: int = 300) -> None:
        """Validate Stripe-Signature: t=timestamp,v1=hex_hmac."""
        parts = {}
        for item in header.split(","):
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            parts.setdefault(key.strip(), []).append(value.strip())

        timestamp = (parts.get("t") or [None])[0]
        signatures = parts.get("v1") or []
        if not timestamp or not signatures:
            raise StripeGatewayError("Malformed Stripe-Signature header", status_code=400)

        try:
            ts = int(timestamp)
        except ValueError as exc:
            raise StripeGatewayError("Invalid Stripe signature timestamp", status_code=400) from exc

        if abs(int(time.time()) - ts) > tolerance_sec:
            raise StripeGatewayError("Stripe webhook timestamp outside tolerance", status_code=400)

        signed_payload = f"{timestamp}.".encode("utf-8") + body
        expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
            raise StripeGatewayError("Invalid Stripe webhook signature", status_code=400)
