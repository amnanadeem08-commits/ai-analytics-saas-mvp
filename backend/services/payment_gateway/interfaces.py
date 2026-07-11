from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class CheckoutSession:
    """Provider-agnostic checkout / payment session."""

    session_id: str
    provider: str
    invoice_id: str
    organization_id: str
    amount_cents: int
    currency: str = "USD"
    status: str = "pending"  # pending | succeeded | failed | cancelled
    checkout_url: str = ""
    provider_reference: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentResult:
    success: bool
    provider: str
    invoice_id: str
    provider_reference: str = ""
    amount_cents: int = 0
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WebhookEvent:
    event_type: str
    provider: str
    invoice_id: str = ""
    provider_reference: str = ""
    amount_cents: int = 0
    paid: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PaymentGateway(Protocol):
    @property
    def name(self) -> str: ...

    def is_live(self) -> bool:
        """True when configured for real external charges."""
        ...

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
    ) -> CheckoutSession: ...

    def verify_webhook(self, *, headers: dict[str, str], body: bytes) -> WebhookEvent: ...
