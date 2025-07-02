"""Pytest fixtures for API v1 tests."""

from io import BytesIO
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.file import File as FileModel
from app.models.user import User


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock regular user."""
    user = Mock(spec=User)
    user.id = 1
    user.is_superuser = False
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_superuser():
    """Mock superuser."""
    user = Mock(spec=User)
    user.id = 2
    user.is_superuser = True
    user.email = "admin@example.com"
    return user


@pytest.fixture
def mock_file_model():
    """Mock file model."""
    file_model = Mock(spec=FileModel)
    file_model.id = 1
    file_model.filename = "test_image.jpg"
    file_model.filepath = "/tmp/test_image.jpg"
    file_model.content_type = "image/jpeg"
    file_model.owner_id = 1
    return file_model


@pytest.fixture
def sample_image_file():
    """Create a sample image file for testing."""
    # Create a simple PNG file content (minimal PNG header)
    png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x12IDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82"
    return BytesIO(png_content)
