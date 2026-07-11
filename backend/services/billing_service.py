from __future__ import annotations

"""Billing engine — invoicing + payment gateway integration."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.billing_models import (
    CreditBalance,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    PaymentAttempt,
    PaymentAttemptStatus,
)
from backend.services.payment_gateway import (
    CheckoutSession,
    PaymentGatewayConfigError,
    StripeGatewayError,
    gateway_status,
    get_payment_gateway,
    get_payment_gateway_config,
    reset_payment_gateway,
)
from backend.services.subscription_service import get_plan, get_subscription
from backend.services.usage_service import aggregate_usage

# Overage unit prices in cents (internal estimates)
_OVERAGE_UNIT_CENTS: dict[str, int] = {
    "ai_requests": 2,
    "tokens": 0,
    "workflow_executions": 10,
    "storage_bytes": 0,
    "api_requests": 1,
}


class BillingError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


_CHECKOUT_SESSIONS: dict[str, CheckoutSession] = {}


def _stores():
    from backend.repositories.commercial_registry import get_commercial_stores

    return get_commercial_stores()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uid(prefix: str = "inv") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def reset_billing() -> None:
    global _CHECKOUT_SESSIONS
    stores = _stores()
    stores.invoices.clear()
    stores.credits.clear()
    stores.payments.clear()
    _CHECKOUT_SESSIONS = {}
    reset_payment_gateway()


def get_credit_balance(organization_id: str) -> CreditBalance:
    bal = _stores().credits.get(organization_id)
    if bal is None:
        bal = CreditBalance(
            balance_id=_uid("cred"),
            organization_id=organization_id,
            balance_cents=0,
            updated_at=_now_iso(),
        )
        _stores().credits.save(bal)
    return bal.model_copy(deep=True)


def add_credit(organization_id: str, amount_cents: int) -> CreditBalance:
    bal = _stores().credits.get(organization_id) or CreditBalance(
        balance_id=_uid("cred"),
        organization_id=organization_id,
        balance_cents=0,
        updated_at=_now_iso(),
    )
    bal.balance_cents += int(amount_cents)
    bal.updated_at = _now_iso()
    _stores().credits.save(bal)
    return bal.model_copy(deep=True)


def estimated_charges(organization_id: str) -> dict[str, Any]:
    sub = get_subscription(organization_id)
    plan = get_plan(sub.plan_id) if sub else get_plan("free")
    base = plan.price_cents if plan else 0
    usage = aggregate_usage(organization_id=organization_id)
    overage_cents = 0
    overage_lines: list[dict[str, Any]] = []
    if plan:
        for limit in plan.limits:
            mkey = limit.metric.value if hasattr(limit.metric, "value") else str(limit.metric)
            used = usage.get(mkey, 0.0)
            if limit.limit_value and used > limit.limit_value:
                excess = used - limit.limit_value
                unit = _OVERAGE_UNIT_CENTS.get(mkey, 0)
                amount = int(excess * unit)
                overage_cents += amount
                overage_lines.append({"metric": mkey, "excess": excess, "amount_cents": amount})
    credit = get_credit_balance(organization_id).balance_cents
    total = max(0, base + overage_cents - credit)
    return {
        "organization_id": organization_id,
        "plan_id": plan.plan_id if plan else "free",
        "base_cents": base,
        "overage_cents": overage_cents,
        "credit_cents": credit,
        "estimated_total_cents": total,
        "currency": "USD",
        "overage_lines": overage_lines,
        "usage": usage,
    }


def generate_invoice(organization_id: str) -> Invoice:
    sub = get_subscription(organization_id)
    estimate = estimated_charges(organization_id)
    now = datetime.now(timezone.utc)
    period_start = sub.current_period_start if sub else _now_iso()
    period_end = (
        sub.current_period_end
        if sub
        else (now + timedelta(days=30)).isoformat().replace("+00:00", "Z")
    )

    items: list[InvoiceItem] = []
    plan = get_plan(estimate["plan_id"])
    if plan and plan.price_cents:
        items.append(
            InvoiceItem(
                item_id=_uid("item"),
                description=f"{plan.name} subscription",
                quantity=1,
                unit_price_cents=plan.price_cents,
                amount_cents=plan.price_cents,
            )
        )
    for line in estimate["overage_lines"]:
        items.append(
            InvoiceItem(
                item_id=_uid("item"),
                description=f"Overage: {line['metric']}",
                metric=line["metric"],
                quantity=line["excess"],
                unit_price_cents=_OVERAGE_UNIT_CENTS.get(line["metric"], 0),
                amount_cents=line["amount_cents"],
            )
        )

    subtotal = sum(i.amount_cents for i in items)
    credit = get_credit_balance(organization_id)
    credit_applied = min(credit.balance_cents, subtotal)
    total = subtotal - credit_applied

    invoice = Invoice(
        invoice_id=_uid(),
        organization_id=organization_id,
        subscription_id=sub.subscription_id if sub else "",
        status=InvoiceStatus.open,
        period_start=period_start,
        period_end=period_end,
        subtotal_cents=subtotal,
        credit_applied_cents=credit_applied,
        total_cents=total,
        items=items,
        issued_at=_now_iso(),
        due_at=(now + timedelta(days=14)).isoformat().replace("+00:00", "Z"),
    )
    _stores().invoices.save(invoice)
    if credit_applied:
        add_credit(organization_id, -credit_applied)
    return invoice.model_copy(deep=True)


def list_invoices(*, organization_id: str | None = None) -> list[Invoice]:
    return _stores().invoices.list(organization_id=organization_id)


def get_invoice(invoice_id: str) -> Invoice | None:
    return _stores().invoices.get(invoice_id)


def get_gateway_status() -> dict[str, Any]:
    return gateway_status()


def start_checkout(
    invoice_id: str,
    *,
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> CheckoutSession:
    invoice = get_invoice(invoice_id)
    if invoice is None:
        raise BillingError(f"Invoice not found: {invoice_id}", status_code=404)
    if invoice.status == InvoiceStatus.paid:
        raise BillingError("Invoice is already paid", status_code=409)
    if invoice.status not in {InvoiceStatus.open, InvoiceStatus.overdue, InvoiceStatus.draft}:
        raise BillingError(
            f"Invoice status does not allow checkout: {invoice.status.value}",
            status_code=409,
        )

    config = get_payment_gateway_config()
    try:
        gateway = get_payment_gateway()
    except PaymentGatewayConfigError as exc:
        raise BillingError(exc.message, status_code=exc.status_code) from exc

    try:
        session = gateway.create_checkout(
            invoice_id=invoice.invoice_id,
            organization_id=invoice.organization_id,
            amount_cents=invoice.total_cents,
            currency=invoice.currency,
            success_url=success_url or config.default_success_url,
            cancel_url=cancel_url or config.default_cancel_url,
            description=f"Data Bot AI invoice {invoice.invoice_id}",
            metadata={"invoice_id": invoice.invoice_id, "organization_id": invoice.organization_id},
        )
    except StripeGatewayError as exc:
        raise BillingError(exc.message, status_code=exc.status_code) from exc

    _CHECKOUT_SESSIONS[session.session_id] = session

    if session.status == "succeeded":
        _mark_invoice_paid(
            invoice.invoice_id,
            amount_cents=invoice.total_cents,
            provider=gateway.name,
            provider_reference=session.provider_reference,
            metadata={"checkout_session_id": session.session_id, "path": "checkout_auto_complete"},
        )
    else:
        attempt = PaymentAttempt(
            attempt_id=_uid("pay"),
            invoice_id=invoice.invoice_id,
            organization_id=invoice.organization_id,
            amount_cents=invoice.total_cents,
            status=PaymentAttemptStatus.pending,
            provider=gateway.name,
            created_at=_now_iso(),
            metadata={
                "checkout_session_id": session.session_id,
                "checkout_url": session.checkout_url,
            },
        )
        _stores().payments.save(attempt)

    return session


def handle_payment_webhook(*, provider: str, headers: dict[str, str], body: bytes) -> dict[str, Any]:
    provider_name = (provider or "").strip().lower()
    if provider_name != "stripe":
        raise BillingError(f"Unsupported webhook provider: {provider}", status_code=400)

    try:
        from backend.services.payment_gateway.stripe_gateway import StripePaymentGateway

        gateway = StripePaymentGateway(get_payment_gateway_config())
        event = gateway.verify_webhook(headers=headers, body=body)
    except StripeGatewayError as exc:
        raise BillingError(exc.message, status_code=exc.status_code) from exc

    if not event.paid:
        return {
            "success": True,
            "handled": False,
            "event_type": event.event_type,
            "reason": "not_a_paid_event",
        }

    if not event.invoice_id:
        raise BillingError("Webhook missing invoice_id / client_reference_id", status_code=400)

    invoice = get_invoice(event.invoice_id)
    if invoice is None:
        raise BillingError(f"Invoice not found for webhook: {event.invoice_id}", status_code=404)

    if invoice.status != InvoiceStatus.paid:
        _mark_invoice_paid(
            invoice.invoice_id,
            amount_cents=event.amount_cents or invoice.total_cents,
            provider="stripe",
            provider_reference=event.provider_reference,
            metadata={"event_type": event.event_type, "path": "webhook"},
        )

    return {
        "success": True,
        "handled": True,
        "event_type": event.event_type,
        "invoice_id": event.invoice_id,
        "provider_reference": event.provider_reference,
    }


def record_payment_attempt(invoice_id: str, *, amount_cents: int | None = None) -> PaymentAttempt:
    """Backward-compatible settlement helper via configured payment gateway."""
    invoice = get_invoice(invoice_id)
    if invoice is None:
        raise BillingError(f"Invoice not found: {invoice_id}", status_code=404)

    if amount_cents is not None and amount_cents != invoice.total_cents:
        inv = _stores().invoices.get(invoice_id)
        if inv is None:
            raise BillingError(f"Invoice not found: {invoice_id}", status_code=404)
        inv.total_cents = int(amount_cents)
        _stores().invoices.save(inv)

    session = start_checkout(invoice_id)
    if session.status != "succeeded":
        return PaymentAttempt(
            attempt_id=_uid("pay"),
            invoice_id=invoice_id,
            organization_id=invoice.organization_id,
            amount_cents=session.amount_cents,
            status=PaymentAttemptStatus.pending,
            provider=session.provider,
            created_at=_now_iso(),
            metadata={
                "checkout_session_id": session.session_id,
                "checkout_url": session.checkout_url,
            },
        )

    for attempt in _stores().payments.list(invoice_id=invoice_id):
        if attempt.status == PaymentAttemptStatus.succeeded:
            return attempt.model_copy(deep=True)

    return _mark_invoice_paid(
        invoice_id,
        amount_cents=session.amount_cents,
        provider=session.provider,
        provider_reference=session.provider_reference,
        metadata={"checkout_session_id": session.session_id},
    )


def _mark_invoice_paid(
    invoice_id: str,
    *,
    amount_cents: int,
    provider: str,
    provider_reference: str = "",
    metadata: dict[str, Any] | None = None,
) -> PaymentAttempt:
    invoice = _stores().invoices.get(invoice_id)
    if invoice is None:
        raise BillingError(f"Invoice not found: {invoice_id}", status_code=404)

    attempt = PaymentAttempt(
        attempt_id=_uid("pay"),
        invoice_id=invoice_id,
        organization_id=invoice.organization_id,
        amount_cents=amount_cents,
        status=PaymentAttemptStatus.succeeded,
        provider=provider,
        created_at=_now_iso(),
        completed_at=_now_iso(),
        metadata={**(metadata or {}), "provider_reference": provider_reference},
    )
    _stores().payments.save(attempt)
    invoice.status = InvoiceStatus.paid
    invoice.paid_at = _now_iso()
    invoice.metadata = {
        **dict(invoice.metadata or {}),
        "payment_provider": provider,
        "provider_reference": provider_reference,
    }
    _stores().invoices.save(invoice)
    return attempt.model_copy(deep=True)
