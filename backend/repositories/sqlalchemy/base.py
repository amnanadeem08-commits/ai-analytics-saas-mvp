from __future__ import annotations

"""Shared base for SQLAlchemy repositories (Sprint 8.2).

Supports two modes:
- Standalone (default): each operation runs in its own session and commits
  immediately — used by the repository registry as long-lived singletons.
- Shared session: when a ``session`` is provided (e.g. by a TransactionManager /
  repository_context), operations use that session and defer commit to the
  caller for atomic multi-repository writes.
"""

from contextlib import contextmanager
from typing import Callable, Iterator

from sqlalchemy.orm import Session

from backend.database.session import session_scope


class SQLAlchemyRepositoryBase:
    def __init__(self, session: Session | None = None):
        self._shared_session = session

    @contextmanager
    def _unit(self, *, write: bool = False) -> Iterator[Session]:
        if self._shared_session is not None:
            session = self._shared_session
            yield session
            if write:
                session.flush()
        else:
            with session_scope() as session:
                yield session
