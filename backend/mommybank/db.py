"""SQLite engine/session. WAL + foreign keys; SQLAlchemy binds every parameter."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_config


def utcnow() -> datetime:
    """Naive UTC — everything stored in DB is naive UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt: datetime) -> str:
    return dt.isoformat() + "Z"


class Base(DeclarativeBase):
    pass


def _db_url(path: str) -> str:
    Path(path).resolve().parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        cfg = get_config()
        # tests set MOMMYBANK_DB before first import; allow explicit override too
        path = os.environ.get("MOMMYBANK_DB", cfg.db_path)
        _engine = create_engine(
            _db_url(path),
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(_engine, "connect")
        def _on_connect(dbapi_conn, _record):  # pragma: no cover - driver glue
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.close()

        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def SessionLocal():  # noqa: N802 - factory function
    get_engine()
    return _SessionLocal()


def get_db():
    """FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
