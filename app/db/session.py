from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Store the engine and sessionmaker as module-level variables
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_session_local():
    """Get or create the sessionmaker."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return _SessionLocal()


def get_db() -> Generator:
    """Dependency for getting async DB session."""
    db = get_session_local()
    try:
        yield db
    finally:
        db.close()
