"""Pytest configuration and fixtures for CRUD tests."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session


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
