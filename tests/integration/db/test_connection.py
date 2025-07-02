"""Tests for database connection and schema."""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base


def test_db_connection():
    """Test that we can connect to the database."""
    engine = create_engine(settings.DATABASE_URL)
    connection = engine.connect()
    assert connection is not None
    connection.close()


def test_required_tables_exist():
    """Test that all required database tables exist."""
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)

    # Get all table names from SQLAlchemy metadata
    expected_tables = set(Base.metadata.tables.keys())

    # Get all tables that actually exist in the database
    existing_tables = set(inspector.get_table_names())

    # Check that all expected tables exist
    missing_tables = expected_tables - existing_tables
    assert not missing_tables, f"Missing tables: {missing_tables}"


def test_table_columns():
    """Test that required columns exist in each table."""
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)

    for table_name, table in Base.metadata.tables.items():
        # Get expected columns
        expected_columns = {column.name for column in table.columns}

        # Get actual columns
        actual_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }

        # Check that all expected columns exist
        missing_columns = expected_columns - actual_columns
        assert (
            not missing_columns
        ), f"Table '{table_name}' is missing columns: {missing_columns}"
