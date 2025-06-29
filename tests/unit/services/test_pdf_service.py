"""Tests for the PDF service module."""

import io
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import img2pdf
import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file import File as FileModel
from app.schemas.file import FileCreate
from app.services.pdf_service import TEMP_DIR, convert_image_to_pdf, merge_pdfs


class TestPDFService:
    """Test cases for PDF service functions."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Set up test environment before each test and clean up after."""
        # Create a temporary directory for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_temp_dir = TEMP_DIR

        # Patch the TEMP_DIR to use our test directory
        from app.services import pdf_service

        self.original_temp_dir_value = pdf_service.TEMP_DIR
        pdf_service.TEMP_DIR = self.test_dir

        # Create a test image
        self.test_image = self.test_dir / "test.png"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(self.test_image, "PNG")

        # Create a test PDF
        self.test_pdf = self.test_dir / "test.pdf"
        with open(self.test_pdf, "wb") as f:
            f.write(img2pdf.convert([self.test_image]))

        yield

        # Cleanup
        shutil.rmtree(self.test_dir, ignore_errors=True)
        pdf_service.TEMP_DIR = self.original_temp_dir_value

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = MagicMock(spec=Session)
        return db

    @pytest.fixture
    def mock_file(self):
        """Create a mock file for testing."""
        from app.models.file import File

        file = File(
            id=1,
            filename="test.png",
            filepath="/path/to/test.png",
            content_type="image/png",
            owner_id=1,
        )
        return file

    @pytest.fixture
    def mock_pdf_file(self):
        """Create a mock PDF file for testing."""
        from app.models.file import File

        file = File(
            id=2,
            filename="test2.pdf",
            filepath="/path/to/test2.pdf",
            content_type="application/pdf",
            owner_id=1,
        )
        return file

    @patch("builtins.open", new_callable=MagicMock)
    @patch("img2pdf.convert")
    def test_convert_image_to_pdf_success(
        self, mock_convert, mock_open, mock_db, mock_file
    ):
        """Test successful image to PDF conversion."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = mock_file

        # Mock the PDF conversion
        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/MediaBox[0 0 612 792]/Contents 5 0 R>>endobj\n4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n5 0 obj<</Length 44>>stream\nBT/F1 24 Tf 100 700 Td(Test PDF)Tj ET\nendstream endobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000145 00000 n \n0000000221 00000 n \n0000000274 00000 n \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n400\n%%EOF\n"
        mock_convert.return_value = pdf_content

        # Mock file operations
        mock_file_handle = MagicMock()
        mock_file_handle.__enter__.return_value = mock_file_handle
        mock_file_handle.read.return_value = b"test image content"

        # Create separate mock for output file
        mock_output_handle = MagicMock()
        mock_output_handle.__enter__.return_value = mock_output_handle

        # Side effect to return different mocks for input and output files
        def open_side_effect(filename, mode="r"):
            if "rb" in mode:
                return mock_file_handle
            return mock_output_handle

        mock_open.side_effect = open_side_effect

        # Create a real File object to return
        from app.models.file import File

        result_file = File(
            id=2,
            filename="test.pdf",  # Should match input filename with .pdf extension
            filepath="/path/to/output.pdf",
            content_type="application/pdf",
            owner_id=1,
        )

        # Mock the database add to return our test file
        def mock_add(file):
            file.id = 2
            return file

        mock_db.add.side_effect = mock_add

        # Test
        result = convert_image_to_pdf(mock_db, 1, 1)

        # Verify
        assert result is not None
        assert result.id == 2
        assert result.filename == "test.pdf"  # Should match input filename
        assert result.content_type == "application/pdf"

        # Verify file operations
        assert mock_open.call_count >= 2  # At least one for input and one for output
        mock_file_handle.read.assert_called_once()
        mock_output_handle.write.assert_called_once_with(pdf_content)

    def test_convert_image_to_pdf_file_not_found(self, mock_db):
        """Test image to PDF conversion with non-existent file."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Test & Verify
        with pytest.raises(ValueError, match="File with id 999 not found"):
            convert_image_to_pdf(mock_db, 999, 1)

    @patch("builtins.open", new_callable=MagicMock)
    @patch("img2pdf.convert")
    def test_convert_image_to_pdf_conversion_error(
        self, mock_convert, mock_open, mock_db, mock_file
    ):
        """Test image to PDF conversion with conversion error."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = mock_file

        # Setup mock file for input
        mock_file_handle = MagicMock()
        mock_file_handle.__enter__.return_value = mock_file_handle
        mock_file_handle.read.return_value = b"test image content"

        # Create separate mock for output file (should not be used)
        mock_output_handle = MagicMock()

        # Side effect to return different mocks for input and output files
        def open_side_effect(filename, mode="r"):
            if "rb" in mode:
                return mock_file_handle
            return mock_output_handle

        mock_open.side_effect = open_side_effect

        # Mock the conversion to raise an error
        class MockImageOpenError(Exception):
            pass

        # Replace the actual ImageOpenError with our mock
        import sys

        import img2pdf

        sys.modules["img2pdf"].ImageOpenError = MockImageOpenError

        # Now set up the side effect with our mock error
        mock_convert.side_effect = MockImageOpenError("Invalid image")

        # Test & Verify
        with pytest.raises(ValueError) as exc_info:
            convert_image_to_pdf(mock_db, 1, 1)

        # Verify the error message contains the original error
        assert "Failed to convert image to PDF" in str(exc_info.value)
        assert "Invalid image" in str(exc_info.value)

        # Verify the error was logged
        mock_convert.assert_called_once()

        # Verify file operations
        mock_file_handle.read.assert_called_once()
        mock_output_handle.write.assert_not_called()

        # Verify no database operations were performed
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()

    @patch("pypdf.PdfReader")
    @patch("app.services.pdf_service.settings")
    def test_merge_pdfs_success(
        self, mock_settings, mock_reader_class, mock_db, tmp_path
    ):
        """Test successful PDF merge."""
        # Setup test directory and files
        test_dir = tmp_path / "test_pdfs"
        test_dir.mkdir()

        # Create two test PDF files with valid content
        pdf1_path = test_dir / "test1.pdf"
        pdf2_path = test_dir / "test2.pdf"

        # Create simple PDF content for testing
        pdf_content = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] /Contents 4 0 R\n>>\nendobj\n"
            b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 24 Tf 100 700 Td (Hello, World!) Tj ET\nendstream\nendobj\n"
            b"xref\n0 5\n0000000000 65535 f \n0000000015 00000 n \n0000000060 00000 n \n0000000111 00000 n \n0000000239 00000 n \n"
            b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n354\n%%EOF\n"
        )

        # Write test PDFs
        pdf1_path.write_bytes(pdf_content)
        pdf2_path.write_bytes(pdf_content)

        # Setup mock database files
        mock_file1 = MagicMock()
        mock_file1.id = 1
        mock_file1.filename = "test1.pdf"
        mock_file1.filepath = str(pdf1_path)
        mock_file1.content_type = "application/pdf"
        mock_file1.owner_id = 1

        mock_file2 = MagicMock()
        mock_file2.id = 2
        mock_file2.filename = "test2.pdf"
        mock_file2.filepath = str(pdf2_path)
        mock_file2.content_type = "application/pdf"
        mock_file2.owner_id = 1

        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_file1,
            mock_file2,
        ]

        # Setup mock settings
        output_dir = test_dir / "output"
        output_dir.mkdir()
        mock_settings.UPLOAD_FOLDER = test_dir
        mock_settings.TEMP_DIR = output_dir

        # Mock the database add to return our test file
        # The actual output path is determined by merge_pdfs and stored in result.filepath
        # We'll capture this in the test and update our mock to return it
        actual_output_path = None

        def mock_add(file):
            nonlocal actual_output_path
            file.id = 3
            # The actual filepath will be set by merge_pdfs
            # We'll store it when it's set
            if hasattr(file, "filepath") and file.filepath:
                actual_output_path = file.filepath
            return file

        mock_db.add.side_effect = mock_add

        # Test
        result = merge_pdfs(mock_db, [1, 2], "merged.pdf", 1)

        # Verify
        assert result is not None
        assert result.id == 3
        assert result.filename == "merged.pdf"
        assert result.content_type == "application/pdf"

        # Verify the merged file was created with expected content
        # The actual output path should be in the TEMP_DIR with the given output filename
        assert actual_output_path is not None, "Output file path was not set"
        assert os.path.exists(
            actual_output_path
        ), f"Output file not found at {actual_output_path}"
        assert os.path.getsize(actual_output_path) > 0, "Output file is empty"

        # Verify the merged PDF contains the expected number of pages (2)
        with open(actual_output_path, "rb") as f:
            reader = PdfReader(f)
            assert len(reader.pages) == 2, f"Expected 2 pages, got {len(reader.pages)}"

        # The returned file object should have the same path as the actual output
        assert result.filepath == actual_output_path

    def test_merge_pdfs_file_not_found(self, mock_db, mock_pdf_file):
        """Test merging with non-existent file raises error."""
        # Setup - return only one file when two are requested
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_pdf_file
        ]

        # Test & Verify
        with pytest.raises(ValueError) as exc_info:
            merge_pdfs(mock_db, [1, 3], "output.pdf", 1)

        # Check that the error message contains the missing ID
        assert "not found" in str(exc_info.value)

    def test_merge_pdfs_empty_list(self, mock_db):
        """Test merging with empty file_ids list raises error."""
        # Test & Verify
        with pytest.raises(ValueError) as exc_info:
            merge_pdfs(mock_db, [], "output.pdf", 1)

        # Check the error message
        assert "No PDF files to merge" in str(exc_info.value)
        assert "3" in str(exc_info.value)

    @patch("builtins.open", new_callable=MagicMock)
    @patch("pypdf.PdfReader")
    def test_merge_pdfs_invalid_pdf(
        self, mock_reader_class, mock_open, mock_db, mock_pdf_file
    ):
        """Test merging with invalid PDF raises error."""
        # Setup
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_pdf_file,
            mock_pdf_file,
        ]

        # Setup mock_open to raise an error for the second input file
        def open_side_effect(filename, mode="rb"):
            if "output" in str(filename):
                output_file = MagicMock()
                output_file.__enter__.return_value = output_file
                return output_file

            # For input files
            if not hasattr(open_side_effect, "call_count"):
                open_side_effect.call_count = 0

            open_side_effect.call_count += 1

            if open_side_effect.call_count == 1:
                # First file is valid
                mock_file = MagicMock()
                mock_file.__enter__.return_value = mock_file
                mock_file.read.return_value = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/MediaBox[0 0 612 792]/Contents 5 0 R>>endobj\n4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n5 0 obj<</Length 44>>stream\nBT/F1 24 Tf 100 700 Td(Test PDF 1)Tj ET\nendstream endobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000145 00000 n \n0000000221 00000 n \n0000000274 00000 n \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n400\n%%EOF\n"
                return mock_file
            else:
                # Second file raises error
                raise Exception("Invalid PDF")

        mock_open.side_effect = open_side_effect

        # Mock PdfReader for the first file
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()]  # One page
        mock_reader_class.return_value = mock_reader

        # Test & Verify
        with pytest.raises(ValueError, match="Error reading PDF"):
            merge_pdfs(mock_db, [1, 2], "output.pdf", 1)

        # Verify no database operations were performed
        mock_db.add.assert_not_called()

        # Verify file operations
        assert mock_open.call_count == 2  # One for each input PDF

    @patch("app.services.pdf_service.PdfWriter")
    @patch("app.services.pdf_service.PdfReader")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("os.makedirs")
    @patch("os.path.exists", return_value=True)  # Mock file existence check
    @patch("os.access", return_value=True)  # Mock file readability check
    def test_merge_pdfs_permission_denied(
        self,
        mock_access,
        mock_exists,
        mock_makedirs,
        mock_open,
        mock_reader_class,
        mock_writer_class,
        mock_db,
        mock_pdf_file,
        caplog,
    ):
        """Test merging with permission denied when writing the output file."""
        # Setup test logger
        import logging

        caplog.set_level(logging.DEBUG)
        logger = logging.getLogger(__name__)

        logger.debug("Starting test_merge_pdfs_permission_denied")

        # Setup mock database query
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_pdf_file,
            mock_pdf_file,
        ]

        # Setup mock for PdfReader
        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_reader.pages = [mock_page]  # One page per PDF
        mock_reader_class.return_value = mock_reader

        # Setup mock for PdfWriter
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        # Setup mock for open() to handle input files
        mock_file_handle = MagicMock()
        mock_file_handle.__enter__.return_value = mock_file_handle
        mock_file_handle.read.return_value = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/MediaBox[0 0 612 792]/Contents 5 0 R>>endobj\n4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n5 0 obj<</Length 44>>stream\nBT/F1 24 Tf 100 700 Td(Test PDF 1)Tj ET\nendstream endobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000145 00000 n \n0000000221 00000 n \n0000000274 00000 n \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n400\n%%EOF\n"
        # Track open calls to handle input and output files differently
        open_calls = []

        def open_side_effect(filename, mode="rb"):
            filename_str = str(filename)
            open_calls.append((filename_str, mode))
            logger.debug(f"open() called with filename: {filename_str}, mode: {mode}")

            # For output file, raise PermissionError
            if "output" in filename_str and ("w" in mode or "wb" in mode):
                logger.debug("Raising PermissionError for output file")
                raise PermissionError("Permission denied")

            # For input files, return the mock file handle
            logger.debug("Returning mock file handle for input file")
            return mock_file_handle

        mock_open.side_effect = open_side_effect

        # Test & Verify
        with pytest.raises(PermissionError, match="Permission denied") as exc_info:
            logger.debug("Calling merge_pdfs")
            merge_pdfs(mock_db, [1, 2], "output.pdf", 1)
            logger.debug(f"merge_pdfs raised: {exc_info}")

        logger.debug("Verifying test assertions")

        # Verify no database operations were performed
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()

        # Log all open calls for debugging
        logger.debug(f"All open() calls: {open_calls}")

        # Verify file operations were attempted
        assert (
            len(open_calls) > 0
        ), f"No file operations were attempted. Open calls: {open_calls}"

        # Verify that we tried to open the output file for writing
        output_opened = any(
            call[0].endswith("output.pdf") and ("w" in call[1] or "wb" in call[1])
            for call in open_calls
        )

        assert output_opened, (
            f"Expected to attempt opening output file with name 'output.pdf' in write/binary mode. "
            f"Open calls: {open_calls}"
        )

        # Log PdfReader mock information
        logger.debug(f"PdfReader call count: {mock_reader_class.call_count}")
        logger.debug(f"PdfReader call args: {mock_reader_class.call_args_list}")

        # Verify PdfReader was called with the correct file path
        expected_input_path = mock_pdf_file.filepath
        logger.debug(f"Expected PdfReader to be called with: {expected_input_path}")

        # Check if PdfReader was called at all
        if mock_reader_class.called:
            # Get the actual arguments passed to PdfReader
            reader_calls = mock_reader_class.call_args_list
            assert any(
                len(args) > 0 and str(args[0]) == expected_input_path
                for args, _ in reader_calls
            ), f"PdfReader not called with expected input path: {expected_input_path}"
        else:
            # If PdfReader wasn't called, log the issue and fail the test
            logger.error("PdfReader was not called during test execution")
            logger.error(
                "This suggests the code path that reads PDFs is not being executed"
            )
            logger.error(
                "Check if the test setup is correct or if the implementation has changed"
            )
            assert False, "PdfReader was not called during test execution"

        # Verify PdfWriter was called
        logger.debug(f"PdfWriter call count: {mock_writer_class.call_count}")
        mock_writer_class.assert_called_once()

        logger.debug("Test completed")
