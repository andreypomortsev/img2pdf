from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.api.v1.endpoints.pdfs import router as pdfs_router
from app.core.config import settings
from app.models.user import User
from app.schemas.pdf import MergeTaskResponse

# Test data
TEST_USER_ID = 1
TEST_FILE_IDS = [1, 2, 3]
TEST_OUTPUT_FILENAME = "merged_output.pdf"


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_current_user():
    """Create a mock current user."""
    user = MagicMock(spec=User)
    user.id = TEST_USER_ID
    user.is_superuser = False
    return user


@pytest.fixture
def app():
    """Create a test FastAPI app with the pdfs router."""
    app = FastAPI()
    app.include_router(pdfs_router)
    return app


@pytest.fixture
def client(app, mock_db, mock_current_user):
    """Create a test client with mocked dependencies."""

    # Mock dependencies
    async def override_get_db():
        yield mock_db

    async def override_get_current_active_user():
        return mock_current_user

    # Apply dependency overrides
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = (
        override_get_current_active_user
    )

    # Configure test settings
    settings.TESTING = True

    with TestClient(app) as test_client:
        yield test_client


@patch("app.api.v1.endpoints.pdfs.pdf_service.merge_pdfs_endpoint")
def test_merge_pdfs_success(mock_merge, client, mock_db, mock_current_user):
    """Test successful PDF merge request."""
    # Setup
    mock_response = MergeTaskResponse(task_id="test_task_123")
    mock_merge.return_value = mock_response

    # Execute
    payload = {
        "file_ids": TEST_FILE_IDS,
        "output_filename": TEST_OUTPUT_FILENAME,
    }
    response = client.post(
        "/merge/", json=payload, headers={"Authorization": "Bearer test_token"}
    )

    # Verify
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"task_id": "test_task_123"}

    # Verify service was called with correct arguments
    mock_merge.assert_called_once()
    call_args = mock_merge.call_args[1]
    assert call_args["request"].file_ids == TEST_FILE_IDS
    assert call_args["request"].output_filename == TEST_OUTPUT_FILENAME
    assert call_args["db"] == mock_db
    assert call_args["current_user"] == mock_current_user


def test_merge_pdfs_missing_required_field(client):
    """Test with missing required field in request payload."""
    response = client.post(
        "/merge/",
        json={"file_ids": [1, 2]},  # Missing output_filename
        headers={"Authorization": "Bearer test_token"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_merge_pdfs_empty_file_ids(client):
    """Test with empty file_ids in request payload."""
    response = client.post(
        "/merge/",
        json={"file_ids": [], "output_filename": "test.pdf"},
        headers={"Authorization": "Bearer test_token"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_merge_pdfs_unauthorized():
    """Test unauthorized access."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.v1.endpoints.pdfs import router as pdfs_router

    # Create a test app with the router but no auth overrides
    test_app = FastAPI()
    test_app.include_router(pdfs_router)

    # Create a test client with the test app
    with TestClient(test_app) as test_client:
        # No auth header
        response = test_client.post(
            "/merge/", json={"file_ids": [1, 2], "output_filename": "test.pdf"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Invalid token format
        response = test_client.post(
            "/merge/",
            json={"file_ids": [1, 2], "output_filename": "test.pdf"},
            headers={"Authorization": "InvalidToken"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@patch("app.api.v1.endpoints.pdfs.pdf_service.merge_pdfs_endpoint")
def test_merge_pdfs_service_error(mock_merge, client):
    """Test error handling when service raises an HTTP exception."""
    # Setup service to raise an HTTP exception
    mock_merge.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Service error"
    )

    # Execute
    response = client.post(
        "/merge/",
        json={"file_ids": [1, 2], "output_filename": "test.pdf"},
        headers={"Authorization": "Bearer test_token"},
    )

    # Verify
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.json()
    assert "Service error" in response.json()["detail"]


@patch("app.api.v1.endpoints.pdfs.pdf_service.merge_pdfs_endpoint")
def test_merge_pdfs_internal_server_error(
    mock_merge, client, mock_db, mock_current_user
):
    """Test error handling when service raises an unexpected exception."""
    from fastapi import HTTPException

    # Setup the mock to raise an HTTPException with 500 status code
    mock_merge.side_effect = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An error occurred while processing your request",
    )

    # Execute the request with valid authentication
    response = client.post(
        "/merge/",
        json={"file_ids": [1, 2], "output_filename": "test.pdf"},
        headers={"Authorization": "Bearer test_token"},
    )

    # Verify the response
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "detail" in response.json()
    assert (
        "An error occurred while processing your request"
        in response.json()["detail"]
    )

    # Verify the service was called with the correct arguments
    mock_merge.assert_called_once()
    call_args = mock_merge.call_args[1]
    assert call_args["request"].file_ids == [1, 2]
    assert call_args["request"].output_filename == "test.pdf"
    assert call_args["current_user"] == mock_current_user


@patch("app.api.v1.endpoints.pdfs.pdf_service.merge_pdfs_endpoint")
def test_merge_pdfs_successful_execution(
    mock_merge, client, mock_db, mock_current_user
):
    """Test the successful execution path of the merge_pdfs_endpoint function."""
    from app.schemas.pdf import MergeTaskResponse

    # Setup the mock to return a successful response
    expected_response = MergeTaskResponse(task_id="test_task_123")
    mock_merge.return_value = expected_response

    # Execute the request with valid authentication
    response = client.post(
        "/merge/",
        json={"file_ids": [1, 2], "output_filename": "test.pdf"},
        headers={"Authorization": "Bearer test_token"},
    )

    # Verify the response
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"task_id": "test_task_123"}

    # Verify the service was called with the correct arguments
    mock_merge.assert_called_once()
    call_args = mock_merge.call_args[1]
    assert call_args["request"].file_ids == [1, 2]
    assert call_args["request"].output_filename == "test.pdf"
    assert call_args["current_user"] == mock_current_user
    assert call_args["db"] == mock_db
