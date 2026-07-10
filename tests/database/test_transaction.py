from __future__ import annotations

import pytest

from backend.database.models.organization import OrganizationORM
from backend.database.transaction import TransactionManager
from tests.database._helpers import teardown_sqlite, use_sqlite_memory


def setup_function():
    use_sqlite_memory()


def teardown_function():
    teardown_sqlite()


def _make_org(org_id: str = "org_txn"):
    return OrganizationORM(
        organization_id=org_id,
        name="Txn Org",
        slug=org_id,
        owner_id="u1",
        status="active",
        created_at="t",
        data={"organization_id": org_id, "name": "Txn Org", "owner_id": "u1", "slug": org_id},
    )


def test_transaction_commit():
    from backend.database.session import new_session

    with TransactionManager() as txn:
        with txn.atomic() as session:
            session.add(_make_org("org_commit"))

    verify = new_session()
    assert verify.get(OrganizationORM, "org_commit") is not None
    verify.close()


def test_transaction_rollback_on_error():
    from backend.database.session import new_session

    txn = TransactionManager()
    with pytest.raises(RuntimeError):
        with txn.atomic() as session:
            session.add(_make_org("org_rollback"))
            raise RuntimeError("fail")
    txn.close()

    verify = new_session()
    assert verify.get(OrganizationORM, "org_rollback") is None
    verify.close()


def test_nested_transaction_savepoint_rollback():
    from backend.database.session import new_session

    txn = TransactionManager()
    with txn.atomic() as session:
        session.add(_make_org("org_outer"))
        # Nested savepoint that rolls back independently.
        try:
            with txn.atomic() as inner:
                inner.add(_make_org("org_inner"))
                raise RuntimeError("inner fail")
        except RuntimeError:
            pass
    txn.commit()
    txn.close()

    verify = new_session()
    assert verify.get(OrganizationORM, "org_outer") is not None
    assert verify.get(OrganizationORM, "org_inner") is None
    verify.close()


def test_repository_context_atomic_writes():
    from backend.database.transaction import repository_context
    from backend.models.organization_models import Organization

    with repository_context() as ctx:
        ctx.repositories["organizations"].add(
            Organization(organization_id="org_ctx", name="Ctx", owner_id="u1", created_at="t")
        )

    # Committed and visible via a fresh standalone repository.
    from backend.repositories.sqlalchemy import SQLAlchemyOrganizationRepository

    repo = SQLAlchemyOrganizationRepository()
    assert repo.get("org_ctx") is not None
