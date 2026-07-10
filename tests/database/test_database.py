from __future__ import annotations

from tests.database._helpers import teardown_sqlite, use_sqlite_memory


def setup_function():
    use_sqlite_memory()


def teardown_function():
    teardown_sqlite()


def test_engine_and_config_resolution():
    from backend.database.config import get_database_config
    from backend.database.session import get_engine

    config = get_database_config()
    assert config.is_sqlite
    assert config.uses_database is True
    engine = get_engine()
    assert engine is not None


def test_init_creates_tables():
    from sqlalchemy import inspect

    from backend.database.session import get_engine

    inspector = inspect(get_engine())
    tables = set(inspector.get_table_names())
    expected = {
        "users",
        "organizations",
        "workspaces",
        "organization_members",
        "invitations",
        "roles",
        "permissions",
        "role_assignments",
        "auth_audit_events",
        "workflow_executions",
        "evaluation_runs",
        "analyst_sessions",
        "knowledge_documents",
        "knowledge_chunks",
    }
    assert expected.issubset(tables)


def test_health_check_connected():
    from backend.database.database import health_check

    result = health_check()
    assert result["connected"] is True
    assert result["dialect"] == "sqlite"


def test_session_scope_commits_and_rolls_back():
    from sqlalchemy import text

    from backend.database.session import session_scope

    with session_scope() as session:
        value = session.execute(text("SELECT 1")).scalar()
        assert value == 1

    import pytest

    with pytest.raises(RuntimeError):
        with session_scope() as session:
            session.execute(text("SELECT 1"))
            raise RuntimeError("boom")
