"""Pytest configuration and fixtures for CRUD tests."""

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import Session, declarative_base

from app.crud.base import CRUDBase

# Create a separate base for tests to avoid table redefinition issues
TestBase = declarative_base()


@pytest.fixture
def db() -> MagicMock:
    """Create a mock database session."""
    mock_db = MagicMock(spec=Session)
    # Configure default return values for common methods
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.query.return_value.get.return_value = None
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = (
        []
    )
    return mock_db


@pytest.fixture
def mock_file_model():
    """Create a mock File model class."""

    class MockFile:
        def __init__(self, **kwargs):
            self.id = kwargs.get("id")
            self.filename = kwargs.get("filename")
            self.content_type = kwargs.get("content_type")
            self.size = kwargs.get("size")
            self.path = kwargs.get("path")
            self.owner_id = kwargs.get("owner_id")

    return MockFile


@pytest.fixture(scope="module")
def test_model():
    """Fixture to define the test SQLAlchemy model."""

    class TestModel(TestBase):
        """Test model for CRUD operations."""

        __tablename__ = "test_model"

        id = Column(Integer, primary_key=True, index=True)
        name = Column(String, nullable=False)
        description = Column(String, nullable=True)
        is_active = Column(Boolean, default=True)

        def __init__(self, **kwargs):
            super().__init__()
            for key, value in kwargs.items():
                setattr(self, key, value)

    return TestModel


@pytest.fixture(scope="module")
def test_schemas():
    """Fixture to define the test Pydantic schemas."""

    class TestCreateSchema(BaseModel):
        """Schema for creating a test model."""

        name: str
        description: str = ""
        is_active: bool = True

    class TestUpdateSchema(BaseModel):
        """Schema for updating a test model."""

        name: str | None = None
        description: str | None = None
        is_active: bool | None = None

    return TestCreateSchema, TestUpdateSchema


@pytest.fixture
def test_crud(test_model, test_schemas):
    """Create a test CRUD instance with the test model and schemas."""
    TestCreateSchema, TestUpdateSchema = test_schemas

    class TestCRUD(CRUDBase[test_model, TestCreateSchema, TestUpdateSchema]):
        """Test CRUD class for testing base functionality."""

        def __init__(self):
            super().__init__(model=test_model)

    return TestCRUD()
