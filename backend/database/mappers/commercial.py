from __future__ import annotations

from backend.database.models.commercial import (
    ApiKeyORM,
    CreditBalanceORM,
    InvoiceORM,
    PaymentAttemptORM,
    SubscriptionORM,
    UsageRecordORM,
)
from backend.models.api_key_models import ApiKey
from backend.models.billing_models import CreditBalance, Invoice, PaymentAttempt, Subscription, UsageRecord


def subscription_to_orm(sub: Subscription, orm: SubscriptionORM | None = None) -> SubscriptionORM:
    target = orm or SubscriptionORM(organization_id=sub.organization_id)
    target.organization_id = sub.organization_id
    target.subscription_id = sub.subscription_id
    target.plan_id = sub.plan_id
    target.status = sub.status.value if hasattr(sub.status, "value") else str(sub.status)
    target.updated_at = sub.updated_at
    target.data = sub.model_dump(mode="json")
    return target


def orm_to_subscription(orm: SubscriptionORM) -> Subscription:
    return Subscription.model_validate(orm.data or {})


def invoice_to_orm(invoice: Invoice, orm: InvoiceORM | None = None) -> InvoiceORM:
    target = orm or InvoiceORM(invoice_id=invoice.invoice_id)
    target.invoice_id = invoice.invoice_id
    target.organization_id = invoice.organization_id
    target.status = invoice.status.value if hasattr(invoice.status, "value") else str(invoice.status)
    target.issued_at = invoice.issued_at
    target.data = invoice.model_dump(mode="json")
    return target


def orm_to_invoice(orm: InvoiceORM) -> Invoice:
    return Invoice.model_validate(orm.data or {})


def credit_to_orm(credit: CreditBalance, orm: CreditBalanceORM | None = None) -> CreditBalanceORM:
    target = orm or CreditBalanceORM(organization_id=credit.organization_id)
    target.organization_id = credit.organization_id
    target.balance_cents = credit.balance_cents
    target.updated_at = credit.updated_at
    target.data = credit.model_dump(mode="json")
    return target


def orm_to_credit(orm: CreditBalanceORM) -> CreditBalance:
    return CreditBalance.model_validate(orm.data or {})


def payment_to_orm(payment: PaymentAttempt, orm: PaymentAttemptORM | None = None) -> PaymentAttemptORM:
    target = orm or PaymentAttemptORM(attempt_id=payment.attempt_id)
    target.attempt_id = payment.attempt_id
    target.invoice_id = payment.invoice_id
    target.organization_id = payment.organization_id
    target.status = payment.status.value if hasattr(payment.status, "value") else str(payment.status)
    target.created_at = payment.created_at
    target.data = payment.model_dump(mode="json")
    return target


def orm_to_payment(orm: PaymentAttemptORM) -> PaymentAttempt:
    return PaymentAttempt.model_validate(orm.data or {})


def usage_to_orm(record: UsageRecord, orm: UsageRecordORM | None = None) -> UsageRecordORM:
    target = orm or UsageRecordORM(record_id=record.record_id)
    target.record_id = record.record_id
    target.organization_id = record.organization_id
    target.workspace_id = record.workspace_id
    target.user_id = record.user_id
    target.metric = record.metric.value if hasattr(record.metric, "value") else str(record.metric)
    target.quantity = float(record.quantity)
    target.recorded_at = record.recorded_at
    target.data = record.model_dump(mode="json")
    return target


def orm_to_usage(orm: UsageRecordORM) -> UsageRecord:
    return UsageRecord.model_validate(orm.data or {})


def api_key_to_orm(key: ApiKey, orm: ApiKeyORM | None = None) -> ApiKeyORM:
    target = orm or ApiKeyORM(key_id=key.key_id)
    target.key_id = key.key_id
    target.organization_id = key.organization_id
    target.key_hash = key.key_hash
    target.status = key.status.value if hasattr(key.status, "value") else str(key.status)
    target.created_at = key.created_at
    target.data = key.model_dump(mode="json")
    return target


def orm_to_api_key(orm: ApiKeyORM) -> ApiKey:
    return ApiKey.model_validate(orm.data or {})
