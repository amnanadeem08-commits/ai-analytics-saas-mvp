from __future__ import annotations

"""Engine + session factory (Sprint 8.2).

Connection pooling is configured for PostgreSQL; SQLite uses appropriate pool
classes automatically (StaticPool for in-memory to share one connection).
"""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.config import DatabaseConfig, get_database_config

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_engine_url: str | None = None


def _build_engine(config: DatabaseConfig) -> Engine:
    kwargs: dict = {"echo": config.echo, "future": True}
    if config.is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
        if config.is_memory_sqlite:
            # Share a single in-memory database across sessions/threads.
            kwargs["poolclass"] = StaticPool
    else:
        # PostgreSQL and other server databases use QueuePool with tuning.
        kwargs["pool_size"] = config.pool_size
        kwargs["pool_timeout"] = config.pool_timeout
        kwargs["max_overflow"] = config.max_overflow
        kwargs["pool_pre_ping"] = True
    return create_engine(config.database_url, **kwargs)


def get_engine() -> Engine:
    global _engine, _session_factory, _engine_url
    config = get_database_config()
    if _engine is None or _engine_url != config.database_url:
        _engine = _build_engine(config)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)
        _engine_url = config.database_url
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


def new_session() -> Session:
    return get_session_factory()()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope: commit on success, rollback on error."""
    session = new_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dispose_engine() -> None:
    """Dispose the engine and reset the cached factory (test/reload helper)."""
    global _engine, _session_factory, _engine_url
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
    _engine_url = None
