"""storage object metadata

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-11 20:05:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "storage_objects",
        sa.Column("object_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("current_checksum", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("object_id"),
    )
    with op.batch_alter_table("storage_objects", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_storage_objects_artifact_type"), ["artifact_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_storage_objects_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_storage_objects_owner_id"), ["owner_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_storage_objects_organization_id"), ["organization_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_storage_objects_workspace_id"), ["workspace_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_storage_objects_current_checksum"), ["current_checksum"], unique=False)
        batch_op.create_index(batch_op.f("ix_storage_objects_created_at"), ["created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("storage_objects", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_storage_objects_created_at"))
        batch_op.drop_index(batch_op.f("ix_storage_objects_current_checksum"))
        batch_op.drop_index(batch_op.f("ix_storage_objects_workspace_id"))
        batch_op.drop_index(batch_op.f("ix_storage_objects_organization_id"))
        batch_op.drop_index(batch_op.f("ix_storage_objects_owner_id"))
        batch_op.drop_index(batch_op.f("ix_storage_objects_status"))
        batch_op.drop_index(batch_op.f("ix_storage_objects_artifact_type"))
    op.drop_table("storage_objects")
