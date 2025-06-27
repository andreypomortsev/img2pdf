"""Unit tests for Celery tasks."""

import os
import uuid
from pathlib import Path
from unittest.mock import ANY, MagicMock, mock_open, patch

import pytest

from app.models.file import File
from app.tasks import convert_image_to_pdf, merge_pdfs


class TestConvertImageToPdf:
    """Tests for the convert_image_to_pdf task."""

    @patch("app.tasks.get_db")
    @patch("app.tasks.img2pdf.convert")
    @patch("builtins.open", new_callable=mock_open, read_data=b"image data")
    @patch("app.tasks.Path")
    @patch("app.tasks.uuid.uuid4")
    def test_convert_image_to_pdf_success(
        self, mock_uuid, mock_path_class, mock_file, mock_convert, mock_get_db
    ):
        """Test successful image to PDF conversion."""
        # Setup mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock the file model that will be returned by the query
        mock_file_model = MagicMock()
        mock_file_model.id = 1
        mock_file_model.filename = "test.png"
        mock_file_model.filepath = "/path/to/test.png"

        # Set up the query chain to return our mock file
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_file_model
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        # Mock path operations
        output_path = Path("/output/1234.pdf")
        mock_path = MagicMock()
        mock_path.parent = MagicMock()
        mock_path.parent.mkdir.return_value = None
        mock_path_class.return_value = output_path

        # Mock UUID for the output filename
        mock_uuid.return_value = "1234"

        # Mock PDF conversion
        mock_convert.return_value = b"pdf data"

        # Mock the new file that will be created
        new_file_id = 2

        # Mock the refresh to set the ID on the new file
        def mock_refresh(file_obj):
            file_obj.id = new_file_id

        mock_db.refresh.side_effect = mock_refresh

        # Execute
        result = convert_image_to_pdf(1)

        # Verify
        assert result == new_file_id  # Should return the new file ID
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify the new file was created with the correct path
        added_file = mock_db.add.call_args[0][0]
        assert isinstance(added_file, FileModel)
        assert added_file.filename == "1234.pdf"
        assert str(added_file.filepath) == str(output_path)


class TestMergePdfs:
    """Tests for the merge_pdfs task."""

    @patch("app.tasks.get_db")
    @patch("PyPDF2.PdfMerger")  # Patch at module level, not in app.tasks
    @patch("builtins.open", new_callable=mock_open)
    @patch("app.tasks.Path")
    @patch("uuid.uuid4")
    def test_merge_pdfs_success(
        self, mock_uuid, mock_path_class, mock_file, mock_pdf_merger, mock_get_db
    ):
        """Test successful PDF merging."""
        # Setup mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock the query chain for getting PDF files
        mock_query = MagicMock()
        mock_filter = MagicMock()

        # Create mock file objects that will be returned by the query
        file1 = MagicMock()
        file1.id = 1
        file1.filename = "1.pdf"
        file1.filepath = "/path/to/1.pdf"

        file2 = MagicMock()
        file2.id = 2
        file2.filename = "2.pdf"
        file2.filepath = "/path/to/2.pdf"

        # Set up the query to return our mock files
        mock_filter.all.return_value = [file1, file2]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        # Mock path operations
        output_path = Path("/output/merged.pdf")
        mock_path = MagicMock()
        mock_path.parent = MagicMock()
        mock_path.parent.mkdir.return_value = None
        mock_path_class.return_value = output_path

        # Mock UUID for the output filename
        mock_uuid.return_value = "1234"

        # Mock PDF merger
        mock_merger = MagicMock()
        mock_pdf_merger.return_value = mock_merger

        # Mock the new file that will be created
        new_file = MagicMock()
        new_file.id = 3  # New file should have a new ID

        # Mock the refresh to set the ID on the new file
        def mock_refresh(file_obj):
            file_obj.id = 3

        mock_db.refresh.side_effect = mock_refresh

        # Execute
        result = merge_pdfs([1, 2], "merged.pdf")

        # Verify database interactions
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify file operations
        assert mock_merger.append.call_count == 2
        mock_merger.write.assert_called_once_with(str(output_path))
        mock_merger.close.assert_called_once()

        # Verify the task returns the new file ID
        assert result == 3
