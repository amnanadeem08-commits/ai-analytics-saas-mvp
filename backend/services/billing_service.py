from __future__ import annotations

"""Billing engine (Sprint 8.6) — internal invoicing, no payment gateway."""

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


_INVOICES: dict[str, Invoice] = {}
_CREDITS: dict[str, CreditBalance] = {}
_PAYMENTS: dict[str, PaymentAttempt] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uid(prefix: str = "inv") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def reset_billing() -> None:
    global _INVOICES, _CREDITS, _PAYMENTS
    _INVOICES = {}
    _CREDITS = {}
    _PAYMENTS = {}


def get_credit_balance(organization_id: str) -> CreditBalance:
    bal = _CREDITS.get(organization_id)
    if bal is None:
        bal = CreditBalance(balance_id=_uid("cred"), organization_id=organization_id, balance_cents=0, updated_at=_now_iso())
        _CREDITS[organization_id] = bal
    return bal.model_copy(deep=True)


def add_credit(organization_id: str, amount_cents: int) -> CreditBalance:
    bal = _CREDITS.get(organization_id) or CreditBalance(
        balance_id=_uid("cred"), organization_id=organization_id, balance_cents=0, updated_at=_now_iso()
    )
    bal.balance_cents += int(amount_cents)
    bal.updated_at = _now_iso()
    _CREDITS[organization_id] = bal.model_copy(deep=True)
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
    period_end = sub.current_period_end if sub else (now + timedelta(days=30)).isoformat().replace("+00:00", "Z")

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
    _INVOICES[invoice.invoice_id] = invoice.model_copy(deep=True)
    if credit_applied:
        add_credit(organization_id, -credit_applied)
    return invoice.model_copy(deep=True)


def list_invoices(*, organization_id: str | None = None) -> list[Invoice]:
    items = list(_INVOICES.values())
    if organization_id:
        items = [i for i in items if i.organization_id == organization_id]
    return [i.model_copy(deep=True) for i in sorted(items, key=lambda x: x.issued_at, reverse=True)]


def get_invoice(invoice_id: str) -> Invoice | None:
    inv = _INVOICES.get(invoice_id)
    return inv.model_copy(deep=True) if inv else None


def record_payment_attempt(invoice_id: str, *, amount_cents: int | None = None) -> PaymentAttempt:
    invoice = get_invoice(invoice_id)
    if invoice is None:
        raise BillingError(f"Invoice not found: {invoice_id}", status_code=404)
    amount = amount_cents if amount_cents is not None else invoice.total_cents
    attempt = PaymentAttempt(
        attempt_id=_uid("pay"),
        invoice_id=invoice_id,
        organization_id=invoice.organization_id,
        amount_cents=amount,
        status=PaymentAttemptStatus.succeeded,
        provider="internal",
        created_at=_now_iso(),
        completed_at=_now_iso(),
        metadata={"note": "Internal billing — no external gateway"},
    )
    _PAYMENTS[attempt.attempt_id] = attempt.model_copy(deep=True)
    inv = _INVOICES[invoice_id]
    inv.status = InvoiceStatus.paid
    inv.paid_at = _now_iso()
    _INVOICES[invoice_id] = inv.model_copy(deep=True)
    return attempt.model_copy(deep=True)
