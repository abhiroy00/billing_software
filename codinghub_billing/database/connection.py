"""Engine/session management. GUI and services never import sqlalchemy.orm
Session directly — they go through ``get_session()`` so the connection
details (SQLite today, PostgreSQL tomorrow) stay isolated here."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from database import models  # noqa: F401  (populates Base.metadata)
from database.base import Base

_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_engine(database_url: str) -> Engine:
    global _engine, _SessionFactory
    _engine = create_engine(database_url, future=True)
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def init_db(database_url: str) -> None:
    """Create the engine (if needed) and ensure all tables exist."""
    engine = _engine if _engine is not None else init_engine(database_url)
    Base.metadata.create_all(engine)


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_db() first.")
    return _engine


@contextmanager
def get_session() -> Iterator[Session]:
    if _SessionFactory is None:
        raise RuntimeError("Database engine not initialized. Call init_db() first.")
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
