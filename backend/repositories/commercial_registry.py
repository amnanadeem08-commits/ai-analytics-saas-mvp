from __future__ import annotations

"""Commercial store registry — memory (default) or SQLAlchemy."""

from dataclasses import dataclass, field

from backend.repositories.commercial_interfaces import (
    ApiKeyStore,
    CreditStore,
    InvoiceStore,
    PaymentStore,
    SubscriptionStore,
    UsageStore,
)
from backend.repositories.commercial_memory import (
    InMemoryApiKeyStore,
    InMemoryCreditStore,
    InMemoryInvoiceStore,
    InMemoryPaymentStore,
    InMemorySubscriptionStore,
    InMemoryUsageStore,
)


@dataclass
class CommercialStoreRegistry:
    subscriptions: SubscriptionStore = field(default_factory=InMemorySubscriptionStore)
    invoices: InvoiceStore = field(default_factory=InMemoryInvoiceStore)
    credits: CreditStore = field(default_factory=InMemoryCreditStore)
    payments: PaymentStore = field(default_factory=InMemoryPaymentStore)
    usage: UsageStore = field(default_factory=InMemoryUsageStore)
    api_keys: ApiKeyStore = field(default_factory=InMemoryApiKeyStore)
    backend: str = "memory"


_COMMERCIAL: CommercialStoreRegistry | None = None


def build_memory_commercial_stores() -> CommercialStoreRegistry:
    return CommercialStoreRegistry(backend="memory")


def build_sqlalchemy_commercial_stores() -> CommercialStoreRegistry:
    from backend.database.database import init_database
    from backend.repositories.sqlalchemy.commercial_repositories import (
        SQLAlchemyApiKeyStore,
        SQLAlchemyCreditStore,
        SQLAlchemyInvoiceStore,
        SQLAlchemyPaymentStore,
        SQLAlchemySubscriptionStore,
        SQLAlchemyUsageStore,
    )

    init_database()
    return CommercialStoreRegistry(
        subscriptions=SQLAlchemySubscriptionStore(),
        invoices=SQLAlchemyInvoiceStore(),
        credits=SQLAlchemyCreditStore(),
        payments=SQLAlchemyPaymentStore(),
        usage=SQLAlchemyUsageStore(),
        api_keys=SQLAlchemyApiKeyStore(),
        backend="postgres",
    )


def _build_from_config() -> CommercialStoreRegistry:
    from backend.database.config import get_database_config
    import os

    # Allow explicit override; otherwise follow STORAGE_BACKEND / database config.
    override = os.getenv("COMMERCIAL_STORAGE_BACKEND", "").strip().lower()
    if override in {"memory", "local", "dev"}:
        return build_memory_commercial_stores()
    if override in {"postgres", "postgresql", "sqlite", "sqlalchemy", "database"}:
        return build_sqlalchemy_commercial_stores()

    config = get_database_config()
    if config.uses_database:
        return build_sqlalchemy_commercial_stores()
    return build_memory_commercial_stores()


def get_commercial_stores() -> CommercialStoreRegistry:
    global _COMMERCIAL
    if _COMMERCIAL is None:
        _COMMERCIAL = _build_from_config()
    return _COMMERCIAL


def set_commercial_stores(registry: CommercialStoreRegistry) -> CommercialStoreRegistry:
    global _COMMERCIAL
    _COMMERCIAL = registry
    return _COMMERCIAL


def reset_commercial_stores(*, backend: str | None = None) -> CommercialStoreRegistry:
    global _COMMERCIAL
    if backend == "memory":
        _COMMERCIAL = build_memory_commercial_stores()
    elif backend in {"postgres", "postgresql", "sqlite", "database", "sqlalchemy"}:
        _COMMERCIAL = build_sqlalchemy_commercial_stores()
    else:
        _COMMERCIAL = _build_from_config()
    return _COMMERCIAL


def clear_commercial_stores() -> None:
    stores = get_commercial_stores()
    stores.subscriptions.clear()
    stores.invoices.clear()
    stores.credits.clear()
    stores.payments.clear()
    stores.usage.clear()
    stores.api_keys.clear()
