from __future__ import annotations

"""Connection pool tuning (Sprint 8.7)."""

from backend.database.config import DatabaseConfig, get_database_config


def optimize_pool_config(config: DatabaseConfig | None = None) -> dict[str, int | bool]:
    """Return recommended pool settings for the active database backend."""
    cfg = config or get_database_config()
    if cfg.is_sqlite:
        return {"pool_pre_ping": False, "pool_size": 1, "max_overflow": 0}
    # PostgreSQL production defaults
    return {
        "pool_size": max(cfg.pool_size, 5),
        "pool_timeout": cfg.pool_timeout,
        "max_overflow": max(cfg.max_overflow, 10),
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }


def pool_status() -> dict[str, object]:
    try:
        from backend.database.session import get_engine

        engine = get_engine()
        pool = engine.pool
        return {
            "dialect": str(engine.dialect.name),
            "pool_class": type(pool).__name__,
            "size": getattr(pool, "size", lambda: None)(),
            "checked_in": getattr(pool, "checkedin", lambda: None)(),
            "checked_out": getattr(pool, "checkedout", lambda: None)(),
            "overflow": getattr(pool, "overflow", lambda: None)(),
        }
    except Exception as exc:
        return {"error": str(exc)}
