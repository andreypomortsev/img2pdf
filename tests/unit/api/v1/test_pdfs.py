from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_user, get_current_user, get_db
from app.main import create_app
from app.models.file import File as FileModel
from app.models.user import User


def get_mock_token() -> str:
    """Generate a mock JWT token for testing."""
    # This is a mock token - in a real test, you'd generate a proper JWT
    return "mock_jwt_token"


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return authentication headers with a mock JWT token."""
    return {"Authorization": f"Bearer {get_mock_token()}"}


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None
    yield mock_session


@pytest.fixture
def mock_current_user():
    """Create a mock current user."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    yield mock_user


@pytest.fixture
def client(mock_db, mock_current_user):
    """Create a test client with mocked dependencies."""
    # Create a fresh app instance for each test
    test_app = create_app()

    # Mock the database session
    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    # Mock the authentication dependencies
    def override_get_current_user():
        return mock_current_user

    def override_get_current_active_user():
        return mock_current_user

    # Apply dependency overrides
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = override_get_current_user
    test_app.dependency_overrides[get_current_active_user] = (
        override_get_current_active_user
    )

    with TestClient(test_app) as test_client:
        yield test_client

    # Clean up overrides after the test
    test_app.dependency_overrides.clear()


@patch("app.api.v1.endpoints.pdfs.file_service.create_merge_task")
@patch("app.api.v1.endpoints.pdfs.crud.file")
def test_merge_pdfs_happy_path(
    mock_crud_file, mock_create_merge_task, client, mock_current_user
):
    """
    Tests the happy path for the /merge/ endpoint with a valid payload.
    """
    # Setup mocks
    mock_task = MagicMock()
    mock_task.id = "test_merge_task_id"
    mock_create_merge_task.return_value = mock_task

    # Mock file access - create a proper File model instance
    mock_file = MagicMock(spec=FileModel)
    mock_file.owner_id = 1
    mock_file.id = 1
    mock_crud_file.get.return_value = mock_file

    # Test
    payload = {"file_ids": [1, 2], "output_filename": "merged.pdf"}
    with client as test_client:
        response = test_client.post(
            "/api/v1/pdfs/merge/",
            json=payload,
            headers={"Authorization": "Bearer mock_token"},
        )

    # Assertions
    assert response.status_code == 202
    assert response.json() == {"task_id": "test_merge_task_id"}
    mock_create_merge_task.assert_called_once_with(
        file_ids=[1, 2], output_filename="merged.pdf"
    )
    # Verify file access was checked
    assert mock_crud_file.get.call_count == 2


def test_merge_pdfs_invalid_payload(client):
    """
    Tests that the /merge/ endpoint returns a 422 error for an invalid payload.
    """
    # Test with missing required field
    payload = {"file_ids": [1, 2]}  # Missing output_filename
    with client as test_client:
        response = test_client.post(
            "/api/v1/pdfs/merge/",
            json=payload,
            headers={"Authorization": "Bearer mock_token"},
        )

    # Should return 422 for validation error
    assert response.status_code == 422
    assert "field required" in str(response.content).lower()


@patch("app.api.v1.endpoints.pdfs.crud.file")
def test_merge_pdfs_unauthorized(mock_crud_file, client):
    """Test that unauthenticated requests are rejected with 401."""
    # Create a test app with only the DB override, not the auth override
    test_app = create_app()

    # Mock the database session
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    # Apply only the DB override, not the auth override
    test_app.dependency_overrides[get_db] = override_get_db

    # Mock file access
    mock_file = MagicMock(spec=FileModel)
    mock_file.owner_id = 1
    mock_crud_file.get.return_value = mock_file

    # Create a new test client without auth overrides
    with TestClient(test_app) as test_client:
        # Test without any auth header
        response = test_client.post(
            "/api/v1/pdfs/merge/",
            json={"file_ids": [1, 2], "output_filename": "test.pdf"},
        )

    # Clean up overrides
    test_app.dependency_overrides.clear()

    # Should fail with 401 before even trying to access the database
    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()

    # Test with invalid token format
    payload = {"file_ids": [1, 2], "output_filename": "test.pdf"}
    with TestClient(test_app) as test_client:
        response = test_client.post(
            "/api/v1/pdfs/merge/",
            json=payload,
            headers={"Authorization": "InvalidTokenFormat"},
        )
    assert (
        response.status_code == 401
    ), f"Expected 401 Unauthorized, got {response.status_code}: {response.text}"
    assert "not authenticated" in response.json()["detail"].lower()

    # Test with invalid token - endpoint returns 403 Forbidden for invalid tokens
    with TestClient(test_app) as test_client:
        response = test_client.post(
            "/api/v1/pdfs/merge/",
            json=payload,
            headers={"Authorization": "Bearer invalid_token"},
        )
    assert (
        response.status_code == 403
    ), f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
    assert "could not validate credentials" in response.json()["detail"].lower()

    # Verify file access was never checked since auth fails first
    mock_crud_file.get.assert_not_called()
