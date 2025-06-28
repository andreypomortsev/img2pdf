"""Tests for the file service module."""

import os
import shutil
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.file import File as FileModel
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
        file_content = b"test file content"
        file = UploadFile(filename="test.txt", file=MagicMock())
        file.file.read.return_value = file_content

        # Mock database operations
        db_file = FileModel(id=1, filename=file.filename, filepath="")
        db.add.return_value = None
        db.flush.return_value = None
        db.refresh.return_value = None
        db.query.return_value.filter.return_value.first.return_value = db_file

        # Act
        service = FileService()
        result = service.save_file(db, file)

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
        file = UploadFile(filename="test.txt", file=MagicMock())
        file.file.read.side_effect = IOError("Failed to read file")

        # Act & Assert
        service = FileService()
        with pytest.raises(IOError, match="Failed to read file"):
            service.save_file(db, file)

    def test_get_file_by_id_found(self):
        """Test retrieving an existing file by ID."""
        # Arrange
        db = MagicMock(spec=Session)
        file_id = 1
        expected_file = FileModel(
            id=file_id, filename="test.txt", filepath="/path/to/file"
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
        result = service.get_file_by_id(db, file_id)

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

        # Mock the query to return None
        query_mock = MagicMock()
        filter_mock = MagicMock()
        first_mock = MagicMock(return_value=None)

        db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = None

        # Act
        service = FileService()
        result = service.get_file_by_id(db, file_id)

        # Assert
        assert result is None
        db.query.assert_called_once_with(FileModel)
        query_mock.filter.assert_called_once()
        filter_mock.first.assert_called_once()

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
        mock_merge_pdfs.delay.assert_called_once_with(file_ids, output_filename)

    @patch("app.services.file_service.merge_pdfs")
    def test_create_merge_task_error(self, mock_merge_pdfs):
        """Test error handling when creating a merge task fails."""
        # Arrange
        file_ids = [1, 2, 3]
        output_filename = "merged.pdf"

        # Make the task raise an exception
        mock_merge_pdfs.delay.side_effect = Exception("Task creation failed")

        # Act & Assert
        service = FileService()
        with pytest.raises(Exception, match="Task creation failed"):
            service.create_merge_task(file_ids, output_filename)

        mock_merge_pdfs.delay.assert_called_once_with(file_ids, output_filename)

    def test_get_file_by_id_database_error(self):
        """Test handling of database errors when getting a file by ID."""
        # Arrange
        db = MagicMock(spec=Session)
        file_id = 1

        # Mock the query to raise an exception
        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.first.side_effect = Exception("Database connection error")
        query_mock.filter.return_value = filter_mock
        db.query.return_value = query_mock

        # Act & Assert
        service = FileService()
        with pytest.raises(Exception, match="Database connection error"):
            service.get_file_by_id(db, file_id)

        # Verify logging occurred
        db.query.assert_called_once_with(FileModel)
        query_mock.filter.assert_called_once()
        filter_mock.first.assert_called_once()
