"""Database connection manager for PostgreSQL."""

import os
import threading
from contextlib import contextmanager
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_engine = None
_SessionFactory = None
_lock = threading.Lock()


def get_database_url() -> str:
    # Prioritize DATABASE_URL if set (used in Docker)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    # Fallback to individual variables
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "scraper_db")
    user = os.getenv("POSTGRES_USER", "scraper_admin")
    password = os.getenv("POSTGRES_PASSWORD", "")
    if not password:
        import warnings
        warnings.warn("POSTGRES_PASSWORD is empty - DB connection will likely fail")
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"


def get_engine():
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = create_engine(
                    get_database_url(),
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                )
    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        with _lock:
            if _SessionFactory is None:
                _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory


@contextmanager
def get_db_session():
    """Context manager that provides a transactional DB session."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
