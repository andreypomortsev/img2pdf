from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status
from sqlalchemy.orm import Session


class TestUploadImageEndpoint:
    """Test the POST /upload-image/ endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self, client, mock_user, sample_image_file):
        self.client = client
        self.mock_user = mock_user
        self.sample_image_file = sample_image_file

    @patch("app.api.v1.endpoints.files.file_service")
    @patch("app.db.session.get_db")
    @patch("app.crud.user.get_by_email")
    @patch("app.api.deps.jwt.decode")
    def test_upload_image_success(
        self,
        mock_jwt_decode,
        mock_get_by_email,
        mock_get_db,
        mock_file_service,
    ):
        """Test successful image upload returns task info."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        mock_get_by_email.return_value = self.mock_user
        mock_jwt_decode.return_value = {"sub": self.mock_user.email}
        mock_file_service.start_image_conversion.return_value = {
            "task_id": "test-task-123",
            "file_id": 1,
        }

        # Reset the file pointer to the beginning
        self.sample_image_file.seek(0)

        # Act
        response = self.client.post(
            "/api/v1/files/upload-image/",
            files={"file": ("test.jpg", self.sample_image_file, "image/jpeg")},
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert data["file_id"] == 1

        # Verify the service was called with correct arguments
        mock_file_service.start_image_conversion.assert_called_once()
        args = mock_file_service.start_image_conversion.call_args[0]
        # Verify the session was passed (don't compare the actual session object)
        assert isinstance(args[0], Session)  # Verify it's a SQLAlchemy session
        # Verify user and file arguments
        assert args[2] == self.mock_user  # current user
        # File argument is UploadFile, check its properties
        uploaded_file = args[1]
        assert uploaded_file.filename == "test.jpg"
        assert uploaded_file.content_type == "image/jpeg"

    @patch("app.api.v1.endpoints.files.file_service")
    @patch("app.db.session.get_db")
    @patch("app.crud.user.get_by_email")
    @patch("app.api.deps.jwt.decode")
    def test_upload_image_invalid_file_type(
        self,
        mock_jwt_decode,
        mock_get_by_email,
        mock_get_db,
        mock_file_service,
    ):
        """Test upload with invalid file type returns 400."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        mock_get_by_email.return_value = self.mock_user
        mock_jwt_decode.return_value = {"sub": self.mock_user.email}
        mock_file_service.start_image_conversion.side_effect = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type: application/pdf",
        )

        # Act
        response = self.client.post(
            "/api/v1/files/upload-image/",
            files={
                "file": ("test.pdf", BytesIO(b"fake pdf"), "application/pdf")
            },
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Unsupported file type: application/pdf"


class TestListFilesEndpoint:
    """Test the GET /files/ endpoint."""

    @patch("app.api.v1.endpoints.files.file_service")
    @patch("app.db.session.get_db")
    @patch("app.crud.user.get_by_email")
    @patch("app.api.deps.jwt.decode")
    def test_list_files_success(
        self,
        mock_jwt_decode,
        mock_get_by_email,
        mock_get_db,
        mock_file_service,
        client,
        mock_user,
    ):
        """Test successful file listing for regular user."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        mock_get_by_email.return_value = mock_user
        mock_jwt_decode.return_value = {"sub": mock_user.email}

        # Create mock file objects with all required fields
        from datetime import datetime, timezone

        # Create mock objects that will be converted to FileSchema
        mock_files = [
            {
                "id": 1,
                "filename": "test1.jpg",
                "content_type": "image/jpeg",
                "size": 1024,
                "owner_id": mock_user.id,
                "filepath": "/tmp/test1.jpg",
                "created_at": datetime(2023, 1, 1, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 1, 1, tzinfo=timezone.utc),
                "url": "http://testserver/files/1",
            },
            {
                "id": 2,
                "filename": "test2.png",
                "content_type": "image/png",
                "size": 2048,
                "owner_id": mock_user.id,
                "filepath": "/tmp/test2.png",
                "created_at": datetime(2023, 1, 2, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 1, 2, tzinfo=timezone.utc),
                "url": "http://testserver/files/2",  # Add full URL for validation
            },
        ]

        # Configure the mock to return our test data
        from app.schemas.file import File

        mock_file_service.list_user_files.return_value = [
            File.model_validate(f) for f in mock_files
        ]

        # Act
        response = client.get(
            "/api/v1/files/", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["filename"] == "test1.jpg"
        assert data[1]["filename"] == "test2.png"

        # Verify the service was called with correct arguments
        # The endpoint calls list_user_files with positional arguments: db, current_user, skip, limit
        args = mock_file_service.list_user_files.call_args[0]

        # Check that first argument is a SQLAlchemy session (not a mock)
        from sqlalchemy.orm import Session as SQLAlchemySession

        assert isinstance(args[0], SQLAlchemySession)  # db

        # Check the user and pagination parameters
        assert args[1] == mock_user  # current_user
        assert args[2] == 0  # skip (default)
        assert args[3] == 100  # limit (default)

    @patch("app.api.v1.endpoints.files.file_service")
    @patch("app.db.session.get_db")
    @patch("app.crud.user.get_by_email")
    @patch("app.api.deps.jwt.decode")
    def test_list_files_with_pagination(
        self,
        mock_jwt_decode,
        mock_get_by_email,
        mock_get_db,
        mock_file_service,
        client,
        mock_user,
    ):
        """Test file listing with pagination parameters."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        mock_get_by_email.return_value = mock_user
        mock_jwt_decode.return_value = {"sub": mock_user.email}
        mock_file_service.list_user_files.return_value = []

        # Act
        response = client.get(
            "/api/v1/files/?skip=10&limit=5",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == 200

        # Check that the function was called with the correct arguments
        # The endpoint calls list_user_files with positional arguments: db, current_user, skip, limit
        args = mock_file_service.list_user_files.call_args[0]

        # Check that first argument is a SQLAlchemy session (not a mock)
        from sqlalchemy.orm import Session as SQLAlchemySession

        assert isinstance(args[0], SQLAlchemySession)  # db

        # Check the user and pagination parameters
        assert args[1] == mock_user  # current_user
        assert args[2] == 10  # skip
        assert args[3] == 5  # limit

    @patch("app.api.v1.endpoints.files.file_service")
    @patch("app.db.session.get_db")
    @patch("app.crud.user.get_by_email")
    @patch("app.api.deps.jwt.decode")
    def test_list_files_empty(
        self,
        mock_jwt_decode,
        mock_get_by_email,
        mock_get_db,
        mock_file_service,
        client,
        mock_user,
    ):
        """Test file listing when user has no files."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        mock_get_by_email.return_value = mock_user
        mock_jwt_decode.return_value = {"sub": mock_user.email}
        mock_file_service.list_user_files.return_value = []

        # Act
        response = client.get(
            "/api/v1/files/", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == 200
        assert response.json() == []

        # Check that the function was called with the correct arguments
        # The endpoint calls list_user_files with positional arguments: db, current_user, skip, limit
        args = mock_file_service.list_user_files.call_args[0]

        # Check that first argument is a SQLAlchemy session (not a mock)
        from sqlalchemy.orm import Session as SQLAlchemySession

        assert isinstance(args[0], SQLAlchemySession)  # db

        # Check the user and pagination parameters
        assert args[1] == mock_user  # current_user
        assert args[2] == 0  # skip (default)
        assert args[3] == 100  # limit (default)

    @patch("app.api.v1.endpoints.files.file_service")
    @patch("app.db.session.get_db")
    @patch("app.crud.user.get_by_email")
    @patch("app.api.deps.jwt.decode")
    def test_list_files_superuser_sees_all(
        self,
        mock_jwt_decode,
        mock_get_by_email,
        mock_get_db,
        mock_file_service,
        client,
        mock_superuser,
    ):
        """Test superuser can see all files from all users."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        mock_get_by_email.return_value = mock_superuser
        mock_jwt_decode.return_value = {"sub": mock_superuser.email}

        # Mock files from different users with all required fields
        from datetime import datetime, timezone

        from app.schemas.file import File

        now = datetime.now(timezone.utc)
        base_url = "http://testserver"

        mock_files = [
            {
                "id": 1,
                "filename": "user1_file.jpg",
                "content_type": "image/jpeg",
                "size": 1024,
                "owner_id": 1,
                "filepath": "/tmp/file1.jpg",
                "created_at": now,
                "updated_at": now,
                "url": f"{base_url}/files/1",
            },
            {
                "id": 2,
                "filename": "user2_file.png",
                "content_type": "image/png",
                "size": 2048,
                "owner_id": 2,
                "filepath": "/tmp/file2.png",
                "created_at": now,
                "updated_at": now,
                "url": f"{base_url}/files/2",
            },
        ]

        # Convert to File objects for proper schema validation
        mock_file_service.list_user_files.return_value = [
            File.model_validate(f) for f in mock_files
        ]

        # Act
        response = client.get(
            "/api/v1/files/", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Superuser sees all files

        # Check that the function was called with the correct arguments
        # The endpoint calls list_user_files with positional arguments: db, current_user, skip, limit
        args = mock_file_service.list_user_files.call_args[0]

        # Check that first argument is a SQLAlchemy session (not a mock)
        from sqlalchemy.orm import Session as SQLAlchemySession

        assert isinstance(args[0], SQLAlchemySession)  # db

        # Check the user and pagination parameters
        assert args[1] == mock_superuser  # current_user (should be superuser)
        assert args[2] == 0  # skip (default)
        assert args[3] == 100  # limit (default)

    def test_list_files_unauthorized(self, client):
        """Test file listing without authentication returns 401."""
        # Act
        response = client.get("/api/v1/files/")

        # Assert
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    @patch("app.api.v1.endpoints.files.file_service")
    @patch("app.db.session.get_db")
    @patch("app.crud.user.get_by_email")
    @patch("app.api.deps.jwt.decode")
    def test_list_files_service_error(
        self,
        mock_jwt_decode,
        mock_get_by_email,
        mock_get_db,
        mock_file_service,
        client,
        mock_user,
    ):
        """Test error handling when file service fails."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        mock_get_by_email.return_value = mock_user
        mock_jwt_decode.return_value = {"sub": mock_user.email}

        # Simulate service error
        mock_file_service.list_user_files.side_effect = HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        )

        # Act
        response = client.get(
            "/api/v1/files/", headers={"Authorization": "Bearer test-token"}
        )

        # Assert HTTP response
        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

        # Check that the function was called with the correct arguments
        # The endpoint calls list_user_files with positional arguments: db, current_user, skip, limit
        args = mock_file_service.list_user_files.call_args[0]

        # Check that first argument is a SQLAlchemy session (not a mock)
        from sqlalchemy.orm import Session as SQLAlchemySession

        assert isinstance(args[0], SQLAlchemySession)  # db

        # Check the user and pagination parameters
        assert args[1] == mock_user  # current_user
        assert args[2] == 0  # skip (default)
        assert args[3] == 100  # limit (default)
