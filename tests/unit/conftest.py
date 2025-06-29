"""Pytest configuration and fixtures for unit tests."""

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import create_app


@pytest.fixture
def mock_db() -> Generator[MagicMock, None, None]:
    """Create a mock database session for unit tests."""
    with patch("sqlalchemy.orm.Session") as mock_session:
        yield mock_session()


@pytest.fixture
def client(mock_db: MagicMock) -> TestClient:
    """Create a test client with mocked database for unit tests."""

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app = create_app()
    # Override the database dependency with our mock
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_current_user():
    """Create a mock current user for testing."""
    from app.models.user import User

    # Create a proper User instance with required attributes
    user = User(
        id=1,
        email="test@example.com",
        username="testuser",
        is_active=True,
        is_superuser=False,
        hashed_password="hashed_test_password",
    )
    return user


@pytest.fixture
def mock_file() -> dict:
    """Create a mock file object for testing."""
    return {
        "id": 1,
        "filename": "test.txt",
        "filepath": "/uploads/test.txt",
        "size": 1024,
        "content_type": "text/plain",
        "owner_id": 1,
    }
