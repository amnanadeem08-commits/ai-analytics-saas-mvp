from __future__ import annotations

from pathlib import Path

ALEMBIC_DIR = Path("alembic")
VERSIONS_DIR = ALEMBIC_DIR / "versions"


def test_alembic_config_and_env_present():
    assert Path("alembic.ini").exists()
    assert (ALEMBIC_DIR / "env.py").exists()
    assert (ALEMBIC_DIR / "script.py.mako").exists()


def test_initial_migration_exists_with_upgrade_downgrade():
    versions = list(VERSIONS_DIR.glob("*.py"))
    assert versions, "No Alembic migration versions found"
    text = "\n".join(v.read_text(encoding="utf-8") for v in versions)
    assert "def upgrade()" in text
    assert "def downgrade()" in text
    # Core tables should be created by the initial migration.
    assert "organizations" in text
    assert "role_assignments" in text
    assert "auth_audit_events" in text


def test_migration_upgrade_downgrade_offline_sql():
    """Render offline SQL for upgrade to validate the migration is executable."""
    import os

    from alembic.config import Config
    from alembic import command

    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["STORAGE_BACKEND"] = "postgres"
    from backend.database.config import reset_database_config

    reset_database_config()

    cfg = Config("alembic.ini")
    # Offline mode renders SQL without touching a live DB (fast + deterministic).
    command.upgrade(cfg, "head", sql=True)
    os.environ["STORAGE_BACKEND"] = "memory"
    os.environ.pop("DATABASE_URL", None)
    reset_database_config()
