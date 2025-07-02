"""Unit tests for the TaskService class."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ServiceError
from app.models.file import File
from app.services.task_service import TaskService, task_service


class TestTaskService:
    """Test cases for the TaskService class."""

    def test_convert_image_to_pdf_success(self):
        """Test successful image to PDF conversion."""
        # Setup
        mock_db = MagicMock(spec=Session)
        mock_file = MagicMock(spec=File)
        mock_file.id = 1
        mock_file.filepath = "/path/to/converted.pdf"

        # Create a mock PDF service
        mock_pdf_service = MagicMock()
        mock_pdf_service.convert_image_to_pdf.return_value = mock_file

        # Patch the pdf_service instance in the task_service module
        with patch("app.services.task_service.pdf_service", mock_pdf_service):
            # Execute
            result = task_service.convert_image_to_pdf(mock_db, 1, 1)

            # Assert
            assert result == {
                "status": "success",
                "file_id": 1,
                "file_path": "/path/to/converted.pdf",
            }
            mock_pdf_service.convert_image_to_pdf.assert_called_once_with(
                mock_db, 1, 1
            )

    def test_convert_image_to_pdf_error(self):
        """Test error handling in image to PDF conversion."""
        # Setup
        mock_db = MagicMock(spec=Session)
        error_msg = "Conversion failed"

        # Create a mock PDF service that raises an error
        mock_pdf_service = MagicMock()
        mock_pdf_service.convert_image_to_pdf.side_effect = ValueError(
            error_msg
        )

        # Patch the pdf_service instance and mock the logger
        with patch(
            "app.services.task_service.pdf_service", mock_pdf_service
        ), patch("app.services.task_service.logger.error") as mock_logger:

            # Execute & Assert
            with pytest.raises(
                ServiceError,
                match=f"Failed to convert image to PDF: {error_msg}",
            ):
                task_service.convert_image_to_pdf(mock_db, 1, 1)

            # Verify error was logged
            mock_logger.assert_called_once()
            assert (
                "Failed to convert image to PDF" in mock_logger.call_args[0][0]
            )
            assert error_msg in str(mock_logger.call_args[0][1])
            assert mock_logger.call_args[1]["exc_info"] is True

    def test_merge_pdfs_success(self):
        """Test successful PDF merging."""
        # Setup
        mock_db = MagicMock(spec=Session)
        mock_file = MagicMock(spec=File)
        mock_file.id = 2
        mock_file.filepath = "/path/to/merged.pdf"

        # Test data
        file_ids = [1, 2, 3]
        output_filename = "merged.pdf"
        owner_id = 1

        # Create a mock PDF service
        mock_pdf_service = MagicMock()
        mock_pdf_service.merge_pdfs.return_value = mock_file

        # Patch the pdf_service instance in the task_service module
        with patch("app.services.task_service.pdf_service", mock_pdf_service):
            # Execute
            result = task_service.merge_pdfs(
                mock_db, file_ids, output_filename, owner_id
            )

            # Assert
            assert result == {
                "status": "success",
                "file_id": 2,
                "file_path": "/path/to/merged.pdf",
            }
            mock_pdf_service.merge_pdfs.assert_called_once_with(
                mock_db, file_ids, output_filename, owner_id
            )

    def test_merge_pdfs_error(self):
        """Test error handling in PDF merging."""
        # Setup
        mock_db = MagicMock(spec=Session)
        error_msg = "Merge failed"

        # Test data
        file_ids = [1, 2, 3]
        output_filename = "merged.pdf"
        owner_id = 1

        # Create a mock PDF service that raises an error
        mock_pdf_service = MagicMock()
        mock_pdf_service.merge_pdfs.side_effect = ValueError(error_msg)

        # Patch the pdf_service instance and mock the logger
        with patch(
            "app.services.task_service.pdf_service", mock_pdf_service
        ), patch("app.services.task_service.logger.error") as mock_logger:

            # Execute & Assert
            with pytest.raises(
                ServiceError, match=f"Failed to merge PDFs: {error_msg}"
            ):
                task_service.merge_pdfs(
                    mock_db, file_ids, output_filename, owner_id
                )

            # Verify error was logged
            mock_logger.assert_called_once()
            assert "Failed to merge PDFs" in mock_logger.call_args[0][0]
            assert error_msg in str(mock_logger.call_args[0][1])
            assert mock_logger.call_args[1]["exc_info"] is True
