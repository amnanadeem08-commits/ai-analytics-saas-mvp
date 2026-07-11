from __future__ import annotations

from backend.database.mappers.commercial import (
    api_key_to_orm,
    credit_to_orm,
    invoice_to_orm,
    orm_to_api_key,
    orm_to_credit,
    orm_to_invoice,
    orm_to_payment,
    orm_to_subscription,
    orm_to_usage,
    payment_to_orm,
    subscription_to_orm,
    usage_to_orm,
)
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
from backend.repositories.sqlalchemy.base import SQLAlchemyRepositoryBase


class SQLAlchemySubscriptionStore(SQLAlchemyRepositoryBase):
    def save(self, subscription: Subscription) -> Subscription:
        with self._unit(write=True) as s:
            existing = s.get(SubscriptionORM, subscription.organization_id)
            s.merge(subscription_to_orm(subscription, existing))
        return subscription.model_copy(deep=True)

    def get(self, organization_id: str) -> Subscription | None:
        with self._unit() as s:
            orm = s.get(SubscriptionORM, organization_id)
            return orm_to_subscription(orm) if orm else None

    def delete(self, organization_id: str) -> bool:
        with self._unit(write=True) as s:
            orm = s.get(SubscriptionORM, organization_id)
            if orm is None:
                return False
            s.delete(orm)
            return True

    def clear(self) -> None:
        with self._unit(write=True) as s:
            s.query(SubscriptionORM).delete()


class SQLAlchemyInvoiceStore(SQLAlchemyRepositoryBase):
    def save(self, invoice: Invoice) -> Invoice:
        with self._unit(write=True) as s:
            existing = s.get(InvoiceORM, invoice.invoice_id)
            s.merge(invoice_to_orm(invoice, existing))
        return invoice.model_copy(deep=True)

    def get(self, invoice_id: str) -> Invoice | None:
        with self._unit() as s:
            orm = s.get(InvoiceORM, invoice_id)
            return orm_to_invoice(orm) if orm else None

    def list(self, *, organization_id: str | None = None) -> list[Invoice]:
        with self._unit() as s:
            query = s.query(InvoiceORM)
            if organization_id:
                query = query.filter(InvoiceORM.organization_id == organization_id)
            rows = query.all()
            items = [orm_to_invoice(r) for r in rows]
        return sorted(items, key=lambda x: x.issued_at, reverse=True)

    def clear(self) -> None:
        with self._unit(write=True) as s:
            s.query(InvoiceORM).delete()


class SQLAlchemyCreditStore(SQLAlchemyRepositoryBase):
    def save(self, credit: CreditBalance) -> CreditBalance:
        with self._unit(write=True) as s:
            existing = s.get(CreditBalanceORM, credit.organization_id)
            s.merge(credit_to_orm(credit, existing))
        return credit.model_copy(deep=True)

    def get(self, organization_id: str) -> CreditBalance | None:
        with self._unit() as s:
            orm = s.get(CreditBalanceORM, organization_id)
            return orm_to_credit(orm) if orm else None

    def clear(self) -> None:
        with self._unit(write=True) as s:
            s.query(CreditBalanceORM).delete()


class SQLAlchemyPaymentStore(SQLAlchemyRepositoryBase):
    def save(self, payment: PaymentAttempt) -> PaymentAttempt:
        with self._unit(write=True) as s:
            existing = s.get(PaymentAttemptORM, payment.attempt_id)
            s.merge(payment_to_orm(payment, existing))
        return payment.model_copy(deep=True)

    def list(self, *, invoice_id: str | None = None) -> list[PaymentAttempt]:
        with self._unit() as s:
            query = s.query(PaymentAttemptORM)
            if invoice_id:
                query = query.filter(PaymentAttemptORM.invoice_id == invoice_id)
            rows = query.all()
            items = [orm_to_payment(r) for r in rows]
        return sorted(items, key=lambda x: x.created_at, reverse=True)

    def clear(self) -> None:
        with self._unit(write=True) as s:
            s.query(PaymentAttemptORM).delete()


class SQLAlchemyUsageStore(SQLAlchemyRepositoryBase):
    def add(self, record: UsageRecord) -> UsageRecord:
        with self._unit(write=True) as s:
            s.merge(usage_to_orm(record))
        return record.model_copy(deep=True)

    def list(
        self,
        *,
        organization_id: str | None = None,
        workspace_id: str | None = None,
        user_id: str | None = None,
        metric: str | None = None,
    ) -> list[UsageRecord]:
        with self._unit() as s:
            query = s.query(UsageRecordORM)
            if organization_id:
                query = query.filter(UsageRecordORM.organization_id == organization_id)
            if workspace_id:
                query = query.filter(UsageRecordORM.workspace_id == workspace_id)
            if user_id:
                query = query.filter(UsageRecordORM.user_id == user_id)
            if metric:
                query = query.filter(UsageRecordORM.metric == metric)
            rows = query.all()
            return [orm_to_usage(r) for r in rows]

    def clear(self) -> None:
        with self._unit(write=True) as s:
            s.query(UsageRecordORM).delete()


class SQLAlchemyApiKeyStore(SQLAlchemyRepositoryBase):
    def save(self, key: ApiKey) -> ApiKey:
        with self._unit(write=True) as s:
            existing = s.get(ApiKeyORM, key.key_id)
            s.merge(api_key_to_orm(key, existing))
        return key.model_copy(deep=True)

    def get(self, key_id: str) -> ApiKey | None:
        with self._unit() as s:
            orm = s.get(ApiKeyORM, key_id)
            return orm_to_api_key(orm) if orm else None

    def get_by_hash(self, key_hash: str) -> ApiKey | None:
        with self._unit() as s:
            orm = s.query(ApiKeyORM).filter(ApiKeyORM.key_hash == key_hash).first()
            return orm_to_api_key(orm) if orm else None

    def list(self, *, organization_id: str | None = None) -> list[ApiKey]:
        with self._unit() as s:
            query = s.query(ApiKeyORM)
            if organization_id:
                query = query.filter(ApiKeyORM.organization_id == organization_id)
            rows = query.all()
            items = [orm_to_api_key(r) for r in rows]
        return sorted(items, key=lambda x: x.created_at, reverse=True)

    def delete(self, key_id: str) -> bool:
        with self._unit(write=True) as s:
            orm = s.get(ApiKeyORM, key_id)
            if orm is None:
                return False
            s.delete(orm)
            return True

    def clear(self) -> None:
        with self._unit(write=True) as s:
            s.query(ApiKeyORM).delete()
