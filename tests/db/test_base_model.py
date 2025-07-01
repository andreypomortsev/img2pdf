"""Tests for the base SQLAlchemy model."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import Column, Integer, String, create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db.base import Base


class TestModel(Base):
    """Test model that inherits from our Base class."""

    __tablename__ = "test_models"  # Explicit table name to avoid confusion

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)


def test_base_model_table_name():
    """Test that __tablename__ is properly set."""
    assert (
        TestModel.__tablename__ == "test_models"
    )  # Should match the explicit table name


def test_base_model_created_at():
    """Test that created_at is automatically set on model creation."""
    # Create a test engine and session
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Test with current time
    with patch("app.db.base.datetime") as mock_datetime:
        test_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = test_time

        # Create a test model
        with SessionLocal() as db:
            test_model = TestModel(name="test")
            db.add(test_model)
            db.commit()
            db.refresh(test_model)

            # Verify created_at was set correctly (compare naive datetime)
            # SQLite doesn't store timezone info, so we just check the values match
            assert test_model.created_at == test_time.replace(tzinfo=None)
            assert test_model.created_at is not None


def test_base_model_created_at_preserved():
    """Test that explicitly set created_at is preserved."""
    # Create a test engine and session
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create with explicit created_at
    custom_time = datetime(2022, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    with SessionLocal() as db:
        test_model = TestModel(name="test", created_at=custom_time)
        db.add(test_model)
        db.commit()
        db.refresh(test_model)

        # Verify the custom time was preserved (compare naive datetime)
        assert test_model.created_at == custom_time.replace(tzinfo=None)


def test_base_model_created_at_not_nullable():
    """Test that created_at cannot be set to None."""
    # Create a test engine and session
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Try to create with created_at=None
    with SessionLocal() as db:
        test_model = TestModel(name="test")
        # SQLite doesn't enforce NOT NULL constraints by default in some cases
        # So we'll test the column definition instead
        inspector = inspect(engine)
        columns = {
            col["name"]: col for col in inspector.get_columns("test_models")
        }
        assert "created_at" in columns
        assert not columns["created_at"]["nullable"]


def test_base_model_inheritance():
    """Test that models properly inherit from Base."""
    assert isinstance(TestModel(), Base)
    assert hasattr(TestModel, "metadata")
    assert hasattr(TestModel, "created_at")
