"""commercial stores

Revision ID: a1b2c3d4e5f6
Revises: e5e80b7071e5
Create Date: 2026-07-11 19:20:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "e5e80b7071e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_subscriptions",
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("subscription_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("organization_id"),
    )
    with op.batch_alter_table("commercial_subscriptions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_commercial_subscriptions_subscription_id"), ["subscription_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_subscriptions_plan_id"), ["plan_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_subscriptions_status"), ["status"], unique=False)

    op.create_table(
        "commercial_invoices",
        sa.Column("invoice_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("issued_at", sa.String(length=40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("invoice_id"),
    )
    with op.batch_alter_table("commercial_invoices", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_commercial_invoices_organization_id"), ["organization_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_invoices_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_invoices_issued_at"), ["issued_at"], unique=False)

    op.create_table(
        "commercial_credits",
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("balance_cents", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("organization_id"),
    )

    op.create_table(
        "commercial_payments",
        sa.Column("attempt_id", sa.String(length=64), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("attempt_id"),
    )
    with op.batch_alter_table("commercial_payments", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_commercial_payments_invoice_id"), ["invoice_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_payments_organization_id"), ["organization_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_payments_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_payments_created_at"), ["created_at"], unique=False)

    op.create_table(
        "commercial_usage",
        sa.Column("record_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.String(length=40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("record_id"),
    )
    with op.batch_alter_table("commercial_usage", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_commercial_usage_organization_id"), ["organization_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_usage_workspace_id"), ["workspace_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_usage_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_usage_metric"), ["metric"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_usage_recorded_at"), ["recorded_at"], unique=False)

    op.create_table(
        "commercial_api_keys",
        sa.Column("key_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("key_id"),
    )
    with op.batch_alter_table("commercial_api_keys", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_commercial_api_keys_organization_id"), ["organization_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_api_keys_key_hash"), ["key_hash"], unique=False)
        batch_op.create_index(batch_op.f("ix_commercial_api_keys_status"), ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("commercial_api_keys")
    op.drop_table("commercial_usage")
    op.drop_table("commercial_payments")
    op.drop_table("commercial_credits")
    op.drop_table("commercial_invoices")
    op.drop_table("commercial_subscriptions")
