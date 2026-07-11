from __future__ import annotations

from backend.models.api_key_models import ApiKey
from backend.models.billing_models import CreditBalance, Invoice, PaymentAttempt, Subscription, UsageRecord


class InMemorySubscriptionStore:
    def __init__(self) -> None:
        self._items: dict[str, Subscription] = {}

    def save(self, subscription: Subscription) -> Subscription:
        self._items[subscription.organization_id] = subscription.model_copy(deep=True)
        return subscription.model_copy(deep=True)

    def get(self, organization_id: str) -> Subscription | None:
        item = self._items.get(organization_id)
        return item.model_copy(deep=True) if item else None

    def delete(self, organization_id: str) -> bool:
        return self._items.pop(organization_id, None) is not None

    def clear(self) -> None:
        self._items.clear()


class InMemoryInvoiceStore:
    def __init__(self) -> None:
        self._items: dict[str, Invoice] = {}

    def save(self, invoice: Invoice) -> Invoice:
        self._items[invoice.invoice_id] = invoice.model_copy(deep=True)
        return invoice.model_copy(deep=True)

    def get(self, invoice_id: str) -> Invoice | None:
        item = self._items.get(invoice_id)
        return item.model_copy(deep=True) if item else None

    def list(self, *, organization_id: str | None = None) -> list[Invoice]:
        items = list(self._items.values())
        if organization_id:
            items = [i for i in items if i.organization_id == organization_id]
        return [i.model_copy(deep=True) for i in sorted(items, key=lambda x: x.issued_at, reverse=True)]

    def clear(self) -> None:
        self._items.clear()


class InMemoryCreditStore:
    def __init__(self) -> None:
        self._items: dict[str, CreditBalance] = {}

    def save(self, credit: CreditBalance) -> CreditBalance:
        self._items[credit.organization_id] = credit.model_copy(deep=True)
        return credit.model_copy(deep=True)

    def get(self, organization_id: str) -> CreditBalance | None:
        item = self._items.get(organization_id)
        return item.model_copy(deep=True) if item else None

    def clear(self) -> None:
        self._items.clear()


class InMemoryPaymentStore:
    def __init__(self) -> None:
        self._items: dict[str, PaymentAttempt] = {}

    def save(self, payment: PaymentAttempt) -> PaymentAttempt:
        self._items[payment.attempt_id] = payment.model_copy(deep=True)
        return payment.model_copy(deep=True)

    def list(self, *, invoice_id: str | None = None) -> list[PaymentAttempt]:
        items = list(self._items.values())
        if invoice_id:
            items = [p for p in items if p.invoice_id == invoice_id]
        return [p.model_copy(deep=True) for p in sorted(items, key=lambda x: x.created_at, reverse=True)]

    def clear(self) -> None:
        self._items.clear()


class InMemoryUsageStore:
    def __init__(self) -> None:
        self._items: list[UsageRecord] = []

    def add(self, record: UsageRecord) -> UsageRecord:
        self._items.append(record.model_copy(deep=True))
        return record.model_copy(deep=True)

    def list(
        self,
        *,
        organization_id: str | None = None,
        workspace_id: str | None = None,
        user_id: str | None = None,
        metric: str | None = None,
    ) -> list[UsageRecord]:
        items = list(self._items)
        if organization_id:
            items = [r for r in items if r.organization_id == organization_id]
        if workspace_id:
            items = [r for r in items if r.workspace_id == workspace_id]
        if user_id:
            items = [r for r in items if r.user_id == user_id]
        if metric:
            items = [r for r in items if r.metric == metric or str(r.metric) == metric]
        return [r.model_copy(deep=True) for r in items]

    def clear(self) -> None:
        self._items.clear()


class InMemoryApiKeyStore:
    def __init__(self) -> None:
        self._items: dict[str, ApiKey] = {}
        self._by_hash: dict[str, str] = {}

    def save(self, key: ApiKey) -> ApiKey:
        # Drop stale hash index if hash changed
        existing = self._items.get(key.key_id)
        if existing and existing.key_hash in self._by_hash:
            del self._by_hash[existing.key_hash]
        self._items[key.key_id] = key.model_copy(deep=True)
        self._by_hash[key.key_hash] = key.key_id
        return key.model_copy(deep=True)

    def get(self, key_id: str) -> ApiKey | None:
        item = self._items.get(key_id)
        return item.model_copy(deep=True) if item else None

    def get_by_hash(self, key_hash: str) -> ApiKey | None:
        key_id = self._by_hash.get(key_hash)
        return self.get(key_id) if key_id else None

    def list(self, *, organization_id: str | None = None) -> list[ApiKey]:
        items = list(self._items.values())
        if organization_id:
            items = [k for k in items if k.organization_id == organization_id]
        return [k.model_copy(deep=True) for k in sorted(items, key=lambda x: x.created_at, reverse=True)]

    def delete(self, key_id: str) -> bool:
        existing = self._items.pop(key_id, None)
        if existing is None:
            return False
        self._by_hash.pop(existing.key_hash, None)
        return True

    def clear(self) -> None:
        self._items.clear()
        self._by_hash.clear()
