import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

def test_db_connection():
    """Test database connection."""
    engine = create_engine(settings.DATABASE_URL)
    connection = engine.connect()
    assert connection is not None
    connection.close()

def test_db_tables_exist():
    """Test that required tables exist."""
    engine = create_engine(settings.DATABASE_URL)
    inspector = engine.connect()
    tables = inspector.execute(
        """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        """
    ).fetchall()
    table_names = {t[0] for t in tables}
    assert 'users' in table_names
    assert 'files' in table_names
