"""
Database connection service.

Exposes:
  - engine       : the SQLAlchemy engine (use for raw SQL or Alembic)
  - SessionLocal : session factory (use get_session() instead in application code)
  - Base         : declarative base for ORM models
  - get_session(): context manager that auto-commits on success, rolls back on error
"""

import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Resolve .env relative to this file's location so it works from any CWD.
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# ── engine ─────────────────────────────────────────────────────────────────────
# DATABASE_URL must be set in .env — no hardcoded credentials anywhere.
# Format: postgresql://user:password@host:port/dbname
_DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    _DATABASE_URL,
    pool_pre_ping=True,      # test connections before use (handles stale connections)
    pool_size=5,             # max permanent connections in pool
    max_overflow=10,         # extra connections allowed under burst load
    echo=False,              # set True to log every SQL statement for debugging
)

# ── session factory ────────────────────────────────────────────────────────────
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ── declarative base ───────────────────────────────────────────────────────────
# ORM model classes created in V3-3 will inherit from this.
class Base(DeclarativeBase):
    pass


# ── session context manager ────────────────────────────────────────────────────
@contextmanager
def get_session():
    """Open a database session, commit on success, roll back on any error.

    Usage:
        with get_session() as session:
            session.add(some_model_instance)
            # commit happens automatically on exit

    Raises:
        Any exception from the database layer — callers should handle or let
        it propagate to the FastAPI exception handler.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── connectivity smoke test (import-time, dev only) ────────────────────────────
def ping() -> str:
    """Run a trivial query to verify the database is reachable.
    Returns the PostgreSQL server version string on success.
    """
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version()")).scalar()
    return row
