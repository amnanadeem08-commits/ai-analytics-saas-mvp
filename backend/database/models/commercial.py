from __future__ import annotations

from typing import Any

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base, JSONType


class SubscriptionORM(Base):
    __tablename__ = "commercial_subscriptions"

    organization_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subscription_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    plan_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="active")
    updated_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class InvoiceORM(Base):
    __tablename__ = "commercial_invoices"

    invoice_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="open")
    issued_at: Mapped[str] = mapped_column(String(40), index=True, default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class CreditBalanceORM(Base):
    __tablename__ = "commercial_credits"

    organization_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    balance_cents: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class PaymentAttemptORM(Base):
    __tablename__ = "commercial_payments"

    attempt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    organization_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    created_at: Mapped[str] = mapped_column(String(40), index=True, default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class UsageRecordORM(Base):
    __tablename__ = "commercial_usage"

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    metric: Mapped[str] = mapped_column(String(64), index=True, default="")
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    recorded_at: Mapped[str] = mapped_column(String(40), index=True, default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class ApiKeyORM(Base):
    __tablename__ = "commercial_api_keys"

    key_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    key_hash: Mapped[str] = mapped_column(String(128), index=True, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="active")
    created_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
