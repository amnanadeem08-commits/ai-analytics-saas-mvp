from __future__ import annotations

"""Transaction management (Sprint 8.2).

Provides a TransactionManager with commit/rollback and nested (savepoint)
transactions, plus a repository context that binds SQLAlchemy repositories to a
single session for atomic multi-repository writes.
"""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session

from backend.database.session import new_session


class TransactionManager:
    """Manage a session lifecycle with commit/rollback and nested savepoints."""

    def __init__(self, session: Session | None = None):
        self._external_session = session is not None
        self.session: Session = session or new_session()

    @contextmanager
    def atomic(self) -> Iterator[Session]:
        """Atomic block: commit on success, rollback on error.

        Uses a SAVEPOINT (nested transaction) when a transaction is already
        active so it composes with outer transactions.
        """
        if self.session.in_transaction():
            nested = self.session.begin_nested()
            try:
                yield self.session
                nested.commit()
            except Exception:
                nested.rollback()
                raise
        else:
            try:
                yield self.session
                self.session.commit()
            except Exception:
                self.session.rollback()
                raise

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        if not self._external_session:
            self.session.close()

    def __enter__(self) -> "TransactionManager":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is not None:
                self.rollback()
        finally:
            self.close()


@contextmanager
def repository_context() -> Iterator["RepositoryContext"]:
    """Yield a RepositoryContext bound to a single session (atomic scope)."""
    from backend.repositories.sqlalchemy import build_sqlalchemy_repositories

    session = new_session()
    try:
        repos = build_sqlalchemy_repositories(session_factory=lambda: session)
        yield RepositoryContext(session=session, repositories=repos)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class RepositoryContext:
    """A set of repositories that share one session for atomic writes."""

    def __init__(self, *, session: Session, repositories) -> None:
        self.session = session
        self.repositories = repositories
