"""Tests for the file service module."""

import shutil
import tempfile
import uuid
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.file import File as FileModel
from app.models.user import User
from app.services.file_service import TEMP_DIR, FileService


class TestFileService:
    """Test cases for FileService class."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Set up test environment before each test and clean up after."""
        # Create a temporary directory for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_temp_dir = TEMP_DIR
        # Patch the TEMP_DIR to use our test directory
        FileService.TEMP_DIR = self.test_dir

        # Setup test file
        self.test_file = self.test_dir / "test.txt"
        with open(self.test_file, "w") as f:
            f.write("test content")

        yield

        # Cleanup
        shutil.rmtree(self.test_dir, ignore_errors=True)
        FileService.TEMP_DIR = self.original_temp_dir

    def test_save_file_success(self):
        """Test saving a file successfully."""
        # Arrange
        db = MagicMock(spec=Session)
        owner_id = 1
        content_type = "text/plain"
        file_content = b"test file content"
        file = UploadFile(filename="test.txt", file=MagicMock())
        file.file.read.return_value = file_content

        # Mock database operations
        db_file = FileModel(
            id=1,
            filename=file.filename,
            filepath=str(self.test_dir / "saved.txt"),
            owner_id=owner_id,
            content_type=content_type,
        )
        db.add.return_value = None
        db.flush.return_value = None
        db.refresh.return_value = None
        db.query.return_value.filter.return_value.first.return_value = db_file

        # Act
        service = FileService()
        result = service.save_file(db, file, owner_id, content_type)

        # Assert
        assert result.filename == file.filename
        assert str(TEMP_DIR) in result.filepath
        assert file.filename in result.filepath

        # Verify the file was written
        saved_file = Path(result.filepath)
        assert saved_file.exists()
        assert saved_file.read_bytes() == file_content

        # Verify database operations
        db.add.assert_called_once()
        db.flush.assert_called_once()
        db.refresh.assert_called_once()

    def test_save_file_io_error(self):
        """Test handling of IOError when saving a file."""
        # Arrange
        db = MagicMock(spec=Session)
        owner_id = 1
        content_type = "text/plain"
        file = UploadFile(filename="test.txt", file=MagicMock())
        file.file.read.side_effect = IOError("Failed to read file")

        # Act & Assert
        service = FileService()
        with pytest.raises(HTTPException) as exc_info:
            service.save_file(db, file, owner_id, content_type)
        assert (
            exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        assert "Failed to save file" in str(exc_info.value.detail)

    def test_get_file_by_id_found(self):
        """Test retrieving an existing file by ID."""
        # Arrange
        db = MagicMock(spec=Session)
        file_id = 1
        owner = MagicMock(spec=User, id=1, is_superuser=False)
        expected_file = FileModel(
            id=file_id,
            filename="test.txt",
            filepath="/path/to/file",
            owner_id=1,
            content_type="text/plain",
        )

        # Mock the query
        query_mock = MagicMock()
        filter_mock = MagicMock()
        first_mock = MagicMock(return_value=expected_file)

        db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = expected_file

        # Act
        service = FileService()
        result = service.get_file_by_id(db, file_id, owner)

        # Assert
        assert result == expected_file
        db.query.assert_called_once_with(FileModel)
        query_mock.filter.assert_called_once()
        filter_mock.first.assert_called_once()

    def test_get_file_by_id_not_found(self):
        """Test retrieving a non-existent file by ID."""
        # Arrange
        db = MagicMock(spec=Session)
        file_id = 999
        owner = MagicMock(id=1, is_superuser=False)

        # Mock the query to return None
        db.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        service = FileService()
        with pytest.raises(HTTPException) as exc_info:
            service.get_file_by_id(db, file_id, owner)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "File not found"
        db.query.assert_called_once_with(FileModel)

    def test_get_file_by_id_permission_denied(self):
        """Test retrieving a file without proper permissions."""
        # Arrange
        db = MagicMock(spec=Session)
        file_id = 1
        owner = MagicMock(id=1, is_superuser=False)
        other_user_file = FileModel(
            id=file_id,
            filename="test.txt",
            filepath="/path/to/file",
            owner_id=2,  # Different owner
        )

        db.query.return_value.filter.return_value.first.return_value = (
            other_user_file
        )

        # Act & Assert
        service = FileService()
        with pytest.raises(HTTPException) as exc_info:
            service.get_file_by_id(db, file_id, owner)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized to access this file" in str(
            exc_info.value.detail
        )

    def test_get_file_by_id_superuser_bypass(self):
        """Test that superusers can access any file regardless of ownership."""
        # Arrange
        db = MagicMock(spec=Session)
        file_id = 1
        superuser = MagicMock(spec=User, id=1, is_superuser=True)
        other_user_file = FileModel(
            id=file_id,
            filename="test.txt",
            filepath="/path/to/file",
            owner_id=2,  # Different owner
            content_type="text/plain",
        )

        db.query.return_value.filter.return_value.first.return_value = (
            other_user_file
        )

        # Act
        service = FileService()
        result = service.get_file_by_id(db, file_id, superuser)

        # Assert
        assert result == other_user_file
        db.query.assert_called_once_with(FileModel)

        # Test with non-existent file
        db.reset_mock()
        db.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.get_file_by_id(db, 999, superuser)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        db.query.assert_called_once_with(FileModel)

    @patch("app.services.file_service.merge_pdfs")
    def test_create_merge_task_success(self, mock_merge_pdfs):
        """Test creating a merge task successfully."""
        # Arrange
        file_ids = [1, 2, 3]
        output_filename = "merged.pdf"

        # Mock the Celery task
        mock_task = MagicMock()
        mock_task.id = str(uuid.uuid4())
        mock_merge_pdfs.delay.return_value = mock_task

        # Act
        service = FileService()
        result = service.create_merge_task(file_ids, output_filename)

        # Assert
        assert result == mock_task
        mock_merge_pdfs.delay.assert_called_once_with(
            file_ids, output_filename
        )

    @patch("app.services.file_service.merge_pdfs")
    def test_create_merge_task_error(self, mock_merge_pdfs):
        """Test error handling when creating a merge task fails."""
        # Arrange
        file_ids = [1, 2, 3]
        output_filename = "merged.pdf"
        db = MagicMock(spec=Session)
        current_user = MagicMock(spec=User, id=1, is_superuser=False)

        # Make the task raise an exception
        mock_merge_pdfs.delay.side_effect = Exception("Task creation failed")

        # Act & Assert
        service = FileService()
        with pytest.raises(HTTPException) as exc_info:
            service.create_merge_task(file_ids, output_filename)
        assert (
            exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        assert "Failed to create merge task" in str(exc_info.value.detail)

        mock_merge_pdfs.delay.assert_called_once_with(
            file_ids, output_filename
        )

    def test_get_file_by_id_database_error(self):
        """Test handling of database errors when getting a file by ID."""
        # Arrange
        db = MagicMock(spec=Session)
        file_id = 1
        current_user = MagicMock(spec=User, id=1, is_superuser=False)

        # Mock the query to raise an exception
        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.first.side_effect = Exception("Database connection error")
        query_mock.filter.return_value = filter_mock
        db.query.return_value = query_mock

        # Act & Assert
        service = FileService()
        with pytest.raises(HTTPException) as exc_info:
            service.get_file_by_id(db, file_id, current_user)
        assert (
            exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        assert "Failed to retrieve file" in str(exc_info.value.detail)

        # Verify logging occurred
        db.query.assert_called_once_with(FileModel)
        query_mock.filter.assert_called_once()
        filter_mock.first.assert_called_once()

    def test_list_user_files_regular_user(self):
        """Test that a regular user can list their own files."""
        # Arrange
        db = MagicMock(spec=Session)
        current_user = MagicMock(spec=User, id=1, is_superuser=False)

        # Create mock files
        mock_files = [
            FileModel(id=1, filename="file1.pdf", owner_id=1),
            FileModel(id=2, filename="file2.pdf", owner_id=1),
        ]

        # Mock the query
        query_mock = MagicMock()
        filter_mock = MagicMock()
        offset_mock = MagicMock()
        limit_mock = MagicMock()

        db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.offset.return_value = offset_mock
        offset_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = mock_files

        # Act
        service = FileService()
        result = service.list_user_files(db, current_user)

        # Assert
        assert len(result) == 2
        assert result[0].filename == "file1.pdf"
        assert result[1].filename == "file2.pdf"
        db.query.assert_called_once_with(FileModel)
        query_mock.filter.assert_called_once()
        filter_mock.offset.assert_called_once_with(0)
        offset_mock.limit.assert_called_once_with(100)
        limit_mock.all.assert_called_once()

    def test_list_user_files_superuser(self):
        """Test that a superuser can list all files."""
        # Arrange
        db = MagicMock(spec=Session)
        current_user = MagicMock(spec=User, id=1, is_superuser=True)

        # Create mock files
        mock_files = [
            FileModel(id=1, filename="file1.pdf", owner_id=1),
            FileModel(
                id=2, filename="file2.pdf", owner_id=2
            ),  # Different owner
        ]

        # Mock the query
        query_mock = MagicMock()
        offset_mock = MagicMock()
        limit_mock = MagicMock()

        db.query.return_value = query_mock
        query_mock.offset.return_value = offset_mock
        offset_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = mock_files

        # Act
        service = FileService()
        result = service.list_user_files(db, current_user)

        # Assert
        assert len(result) == 2
        assert result[0].filename == "file1.pdf"
        assert result[1].filename == "file2.pdf"
        db.query.assert_called_once_with(FileModel)
        query_mock.offset.assert_called_once_with(0)
        offset_mock.limit.assert_called_once_with(100)
        limit_mock.all.assert_called_once()

    def test_list_user_files_pagination(self):
        """Test that pagination works correctly."""
        # Arrange
        db = MagicMock(spec=Session)
        current_user = MagicMock(spec=User, id=1, is_superuser=False)

        # Create mock files
        mock_files = [FileModel(id=3, filename="file3.pdf", owner_id=1)]

        # Mock the query
        query_mock = MagicMock()
        filter_mock = MagicMock()
        offset_mock = MagicMock()
        limit_mock = MagicMock()

        db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.offset.return_value = offset_mock
        offset_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = mock_files

        # Act - Test with custom skip and limit
        service = FileService()
        result = service.list_user_files(db, current_user, skip=2, limit=1)

        # Assert
        assert len(result) == 1
        assert result[0].filename == "file3.pdf"
        db.query.assert_called_once_with(FileModel)
        query_mock.filter.assert_called_once()
        filter_mock.offset.assert_called_once_with(2)
        offset_mock.limit.assert_called_once_with(1)
        limit_mock.all.assert_called_once()

    def test_list_user_files_database_error(self):
        """Test error handling for database errors."""
        # Arrange
        db = MagicMock(spec=Session)
        current_user = MagicMock(id=1, is_superuser=False)

        # Mock the query to raise an exception
        db.query.side_effect = Exception("Database connection error")

        # Act & Assert
        service = FileService()
        with pytest.raises(HTTPException) as exc_info:
            service.list_user_files(db, current_user)

        assert (
            exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        assert "Failed to list files" in str(exc_info.value.detail)

    @patch("app.services.file_service.convert_image_to_pdf")
    def test_start_image_conversion_success(self, mock_convert_task):
        """Test successful image conversion."""
        # Arrange
        db = MagicMock(spec=Session)
        file = MagicMock(spec=UploadFile)
        file.content_type = "image/jpeg"
        file.filename = "test.jpg"
        current_user = MagicMock(id=1, is_superuser=False)

        # Mock the save_file method
        saved_file = FileModel(
            id=1,
            filename="test.jpg",
            filepath="/path/to/test.jpg",
            content_type="image/jpeg",
            owner_id=1,
        )

        # Configure the mock task
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_convert_task.delay.return_value = mock_task

        # Act
        service = FileService()
        with patch.object(
            service, "save_file", return_value=saved_file
        ) as mock_save:
            result = service.start_image_conversion(db, file, current_user)

        # Assert
        assert result == {"task_id": "task-123", "file_id": 1}
        mock_save.assert_called_once()
        mock_convert_task.delay.assert_called_once_with(1)

    def test_start_image_conversion_unsupported_file_type(self):
        """Test conversion with unsupported file type."""
        # Arrange
        db = MagicMock(spec=Session)
        file = MagicMock(spec=UploadFile)
        file.content_type = "text/plain"
        file.filename = "test.txt"
        current_user = MagicMock()

        # Act & Assert
        service = FileService()
        with pytest.raises(HTTPException) as exc_info:
            service.start_image_conversion(db, file, current_user)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported file type" in str(exc_info.value.detail)

    @patch("app.services.file_service.convert_image_to_pdf")
    def test_start_image_conversion_database_error(self, mock_convert_task):
        """Test handling of database errors during file save."""
        # Arrange
        db = MagicMock(spec=Session)
        file = MagicMock(spec=UploadFile)
        file.content_type = "image/png"
        file.filename = "test.png"
        current_user = MagicMock(id=1, is_superuser=False)

        # Configure the mock to raise an exception
        service = FileService()
        with patch.object(
            service, "save_file", side_effect=Exception("Database error")
        ) as mock_save:
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                service.start_image_conversion(db, file, current_user)

            assert (
                exc_info.value.status_code
                == status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            assert "Failed to process file" in str(exc_info.value.detail)
            mock_save.assert_called_once()
            mock_convert_task.delay.assert_not_called()

    @patch("app.services.file_service.convert_image_to_pdf")
    def test_start_image_conversion_processing_error(self, mock_convert_task):
        """Test handling of file processing errors."""
        # Arrange
        db = MagicMock(spec=Session)
        file = MagicMock(spec=UploadFile)
        file.content_type = "image/gif"
        file.filename = "test.gif"
        current_user = MagicMock(id=1, is_superuser=False)

        # Mock the save_file method
        saved_file = FileModel(
            id=1,
            filename="test.gif",
            filepath="/path/to/test.gif",
            content_type="image/gif",
            owner_id=1,
        )

        # Configure the mock task to raise an exception
        mock_convert_task.delay.side_effect = Exception("Processing error")

        # Act & Assert
        service = FileService()
        with patch.object(service, "save_file", return_value=saved_file):
            with pytest.raises(HTTPException) as exc_info:
                service.start_image_conversion(db, file, current_user)

            assert (
                exc_info.value.status_code
                == status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            assert "Failed to process file" in str(exc_info.value.detail)
            mock_convert_task.delay.assert_called_once_with(1)

    @patch("app.services.file_service.AsyncResult")
    @patch("app.services.file_service.celery_app")
    def test_get_task_status_success(self, mock_celery_app, mock_async_result):
        """Test successfully getting task status."""
        # Arrange
        db = MagicMock(spec=Session)
        current_user = MagicMock(id=1, is_superuser=False)
        task_id = "test-task-123"

        # Mock AsyncResult and its methods
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.status = "SUCCESS"
        mock_result.result = {"file_id": 1}
        mock_async_result.return_value = mock_result

        # Mock celery app
        mock_celery_app.return_value = MagicMock()

        # Mock get_file_by_id to return a file
        mock_file = MagicMock()
        mock_file.owner_id = 1  # Same as current_user.id

        # Act
        service = FileService()
        with patch.object(
            service, "get_file_by_id", return_value=mock_file
        ) as mock_get_file:
            result = service.get_task_status(task_id, db, current_user)

        # Assert
        assert result == {
            "task_id": task_id,
            "status": "SUCCESS",
            "result": {"file_id": 1},
        }
        mock_async_result.assert_called_once_with(task_id, app=ANY)
        mock_get_file.assert_called_once_with(db, 1, current_user)

    @patch("app.services.file_service.AsyncResult")
    @patch("app.services.file_service.celery_app")
    def test_get_task_status_pending(self, mock_celery_app, mock_async_result):
        """Test getting status of a pending task."""
        # Arrange
        db = MagicMock(spec=Session)
        current_user = MagicMock(spec=User, id=1, is_superuser=False)
        task_id = "test-task-123"

        # Mock AsyncResult for pending task
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.status = "PENDING"
        mock_async_result.return_value = mock_result

        # Mock celery app
        mock_celery_app.return_value = MagicMock()
        mock_backend = MagicMock()
        mock_backend.result = None
        mock_celery_app.return_value.backend = mock_backend

        # Act
        service = FileService()
        result = service.get_task_status(task_id, db, current_user)

        # Assert
        assert result == {
            "task_id": task_id,
            "status": "PENDING",
            "result": None,
        }
        mock_async_result.assert_called_once_with(task_id, app=ANY)

    @patch("app.services.file_service.AsyncResult")
    @patch("app.services.file_service.celery_app")
    def test_get_task_status_failure(self, mock_celery_app, mock_async_result):
        """Test getting status of a failed task."""
        # Arrange
        db = MagicMock(spec=Session)
        current_user = MagicMock()
        task_id = "test-task-123"
        error_message = "Test error"

        # Mock AsyncResult for failed task
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.status = "FAILURE"
        mock_result.result = Exception(error_message)
        mock_async_result.return_value = mock_result

        # Mock celery app
        mock_celery_app.return_value = MagicMock()

        # Act
        service = FileService()
        result = service.get_task_status(task_id, db, current_user)

        # Assert
        assert result == {
            "task_id": task_id,
            "status": "FAILURE",
            "result": mock_result.result,
        }
        mock_async_result.assert_called_once_with(task_id, app=ANY)

    @patch("app.services.file_service.AsyncResult")
    @patch("app.services.file_service.celery_app")
    def test_get_task_status_unauthorized(
        self, mock_celery_app, mock_async_result
    ):
        """Test getting status of a task with unauthorized access to result."""
        # Arrange
        db = MagicMock(spec=Session)
        current_user = MagicMock(id=1, is_superuser=False)
        task_id = "test-task-123"

        # Mock AsyncResult for completed task
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.status = "SUCCESS"
        mock_result.result = {"file_id": 1}
        mock_async_result.return_value = mock_result

        # Mock celery app
        mock_celery_app.return_value = MagicMock()

        # Mock get_file_by_id to raise 403
        service = FileService()
        with patch.object(
            service,
            "get_file_by_id",
            side_effect=HTTPException(
                status_code=403, detail="Not authorized"
            ),
        ) as mock_get_file:
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                service.get_task_status(task_id, db, current_user)

            assert exc_info.value.status_code == 403
            assert "Not authorized" in str(exc_info.value.detail)
            mock_get_file.assert_called_once_with(db, 1, current_user)

    @patch("app.services.file_service.AsyncResult")
    @patch("app.services.file_service.celery_app")
    def test_get_task_status_invalid_result(
        self, mock_celery_app, mock_async_result
    ):
        """Test getting status with invalid task result format."""
        # Arrange
        db = MagicMock(spec=Session)
        current_user = MagicMock()
        task_id = "test-task-123"

        # Mock AsyncResult with invalid result format
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.status = "SUCCESS"
        mock_result.result = "invalid-result"  # Not a dict
        mock_async_result.return_value = mock_result

        # Mock celery app
        mock_celery_app.return_value = MagicMock()

        # Act
        service = FileService()
        result = service.get_task_status(task_id, db, current_user)

        # Should still return the status even if result format is invalid
        assert result == {
            "task_id": task_id,
            "status": "SUCCESS",
            "result": "invalid-result",
        }
