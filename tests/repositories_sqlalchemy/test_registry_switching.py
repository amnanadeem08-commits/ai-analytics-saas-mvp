from __future__ import annotations

from backend.repositories.registry import (
    build_memory_registry,
    build_sqlalchemy_registry,
    get_repositories,
    reset_repositories,
    set_repositories,
)
from tests.repositories_sqlalchemy._helpers import teardown_sqlite, use_sqlite_memory


def teardown_function():
    teardown_sqlite()
    reset_repositories(backend="memory")


def test_memory_backend_selected_by_default():
    import os

    os.environ["STORAGE_BACKEND"] = "memory"
    from backend.database.config import reset_database_config

    reset_database_config()
    registry = reset_repositories()
    assert registry.backend == "memory"


def test_postgres_backend_selected_from_config():
    use_sqlite_memory()
    registry = reset_repositories()
    assert registry.backend == "postgres"
    # Default RBAC roles seeded in the persistent backend.
    assert len(registry.roles.list()) >= 4


def test_switch_backend_without_touching_services():
    from backend.services import organization_service, rbac_service

    # Memory backend.
    reset_repositories(backend="memory")
    org_mem = organization_service.create_organization(name="MemOrg", owner_id="u1")
    assert rbac_service.has_permission("u1", "organization:delete", organization_id=org_mem.organization_id)

    # Switch to persistent backend — same service code path.
    use_sqlite_memory()
    reset_repositories(backend="postgres")
    org_db = organization_service.create_organization(name="DbOrg", owner_id="u2")
    assert organization_service.get_organization(org_db.organization_id) is not None
    assert rbac_service.has_permission("u2", "organization:delete", organization_id=org_db.organization_id)


def test_registry_seeds_default_rbac_for_both_backends():
    mem = build_memory_registry()
    assert {r.role_id for r in mem.roles.list()} >= {"viewer", "member", "admin", "owner"}

    use_sqlite_memory()
    db = build_sqlalchemy_registry()
    assert {r.role_id for r in db.roles.list()} >= {"viewer", "member", "admin", "owner"}
