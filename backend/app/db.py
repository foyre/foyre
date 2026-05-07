"""Database engine, session, and declarative base.

SQLite by default; Postgres for production. Driver is selected by the
`DATABASE_URL` setting:
  - sqlite:////data/foyre.db
  - postgresql+psycopg://user:pass@host:5432/foyre

`psycopg` (3.x) is in requirements.txt so Postgres works out of the box.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


_is_sqlite = settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

_engine_kwargs: dict = {"future": True, "connect_args": _connect_args}
if not _is_sqlite:
    # Recycle stale pooled connections for Postgres so we don't blow up
    # after the DB or a load balancer idle-times them out.
    _engine_kwargs.update({"pool_pre_ping": True, "pool_recycle": 1800})

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
