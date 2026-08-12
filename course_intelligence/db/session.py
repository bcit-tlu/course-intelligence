"""Database engine and session factory.

Reads DATABASE_URL from config. Normalizes plain postgresql:// URLs to
use the psycopg (v3) driver, so the same URL works in docker-compose
and locally.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from course_intelligence.default_config import DEFAULT_CONFIG

# Local dev fallback — matches the docker-compose db service with its
# published port (5432) on localhost.
_LOCAL_DEV_URL = "postgresql+psycopg://dialog:dialog@localhost:5432/dialog"


def get_database_url() -> str:
    """Return the SQLAlchemy database URL with the psycopg driver."""
    url = DEFAULT_CONFIG.get("database_url") or _LOCAL_DEV_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


_engine = None
_session_factory: sessionmaker[Session] | None = None


def get_engine():
    """Return the shared engine, creating it on first use."""
    global _engine
    if _engine is None:
        _engine = create_engine(get_database_url(), pool_pre_ping=True)
    return _engine


def get_session() -> Session:
    """Create a new database session."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory()
