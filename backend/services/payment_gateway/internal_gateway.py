from __future__ import annotations

import uuid
from typing import Any

from backend.services.payment_gateway.interfaces import CheckoutSession, PaymentGateway, WebhookEvent


class InternalPaymentGateway:
    """Dev/test gateway — settles immediately without an external provider."""

    @property
    def name(self) -> str:
        return "internal"

    def is_live(self) -> bool:
        return False

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
        session_id = f"int_cs_{uuid.uuid4().hex[:16]}"
        meta = dict(metadata or {})
        meta.update({"success_url": success_url, "cancel_url": cancel_url, "description": description})
        # Zero-amount invoices settle as succeeded immediately.
        status = "succeeded" if amount_cents <= 0 else "pending"
        checkout_url = success_url if amount_cents <= 0 else f"{success_url}&session_id={session_id}"
        if amount_cents > 0:
            # Internal gateway can auto-complete on create when explicitly requested via metadata.
            if meta.get("auto_complete", True):
                status = "succeeded"
                checkout_url = success_url
        return CheckoutSession(
            session_id=session_id,
            provider=self.name,
            invoice_id=invoice_id,
            organization_id=organization_id,
            amount_cents=amount_cents,
            currency=currency,
            status=status,
            checkout_url=checkout_url,
            provider_reference=session_id,
            metadata=meta,
        )

    def verify_webhook(self, *, headers: dict[str, str], body: bytes) -> WebhookEvent:
        _ = headers, body
        raise ValueError("Internal gateway does not accept external webhooks")
