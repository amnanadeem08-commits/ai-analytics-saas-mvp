from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.database.config import reset_database_config, set_database_config, DatabaseConfig
from backend.database.database import init_database, reset_database
from backend.database.session import dispose_engine
from backend.repositories.commercial_registry import reset_commercial_stores
from backend.services import api_key_service, billing_service, subscription_service, usage_service
from backend.models.billing_models import UsageMetric


ORG = "org_sql_commercial"


@pytest.fixture()
def sqlite_commercial(tmp_path: Path):
    db_path = tmp_path / "commercial.db"
    url = f"sqlite:///{db_path.as_posix()}"
    dispose_engine()
    reset_database_config()
    set_database_config(
        DatabaseConfig(
            storage_backend="sqlite",
            database_url=url,
            echo=False,
        )
    )
    dispose_engine()
    init_database()
    reset_commercial_stores(backend="sqlite")
    usage_service.reset_usage()
    subscription_service.reset_subscriptions()
    billing_service.reset_billing()
    api_key_service.reset_api_keys()
    yield url
    # Tear down to memory defaults for other tests
    dispose_engine()
    reset_database_config()
    os.environ.pop("COMMERCIAL_STORAGE_BACKEND", None)
    reset_commercial_stores(backend="memory")
    usage_service.reset_usage()
    subscription_service.reset_subscriptions()
    billing_service.reset_billing()
    api_key_service.reset_api_keys()


def test_commercial_sql_persists_across_registry_rebuild(sqlite_commercial):
    subscription_service.assign_plan(ORG, "pro")
    usage_service.record_usage(UsageMetric.ai_requests, 3, organization_id=ORG)
    invoice = billing_service.generate_invoice(ORG)
    billing_service.add_credit(ORG, 250)
    key, raw = api_key_service.create_key(name="persist", organization_id=ORG, created_by="u1")

    invoice_id = invoice.invoice_id
    key_id = key.key_id

    # Rebuild SQL commercial stores against same DB (simulates process restart)
    reset_commercial_stores(backend="sqlite")

    sub = subscription_service.get_subscription(ORG)
    assert sub is not None
    assert sub.plan_id == "pro"

    totals = usage_service.aggregate_usage(organization_id=ORG)
    assert totals.get("ai_requests") == 3

    loaded = billing_service.get_invoice(invoice_id)
    assert loaded is not None
    assert loaded.organization_id == ORG

    credit = billing_service.get_credit_balance(ORG)
    assert credit.balance_cents == 250

    loaded_key = api_key_service.get_key(key_id)
    assert loaded_key is not None
    assert loaded_key.name == "persist"
    auth = api_key_service.authenticate_key(raw)
    assert auth.key_id == key_id


def test_commercial_sql_payment_survives_rebuild(sqlite_commercial):
    subscription_service.assign_plan(ORG, "pro")
    invoice = billing_service.generate_invoice(ORG)
    payment = billing_service.record_payment_attempt(invoice.invoice_id)
    assert payment.status.value == "succeeded"

    reset_commercial_stores(backend="sqlite")
    paid = billing_service.get_invoice(invoice.invoice_id)
    assert paid is not None
    assert paid.status.value == "paid"
