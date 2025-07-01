"""Tests for the PDF service module."""

import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import img2pdf
import pytest
from PIL import Image
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models.file import File


@pytest.fixture
def mock_task_service():
    """Create a mock task service."""
    return MagicMock()


@pytest.fixture
def pdf_service(mock_task_service):
    """Fixture that provides a new PDFService instance."""
    from app.services.pdf_service import PDFService

    return PDFService(task_service=mock_task_service)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_file():
    """Create a mock file for testing."""
    return File(
        id=1,
        filename="test.png",
        filepath="/path/to/test.png",
        content_type="image/png",
        owner_id=1,
    )


@pytest.fixture
def mock_pdf_file():
    """Create a mock PDF file for testing."""
    return File(
        id=2,
        filename="test2.pdf",
        filepath="/path/to/test2.pdf",
        content_type="application/pdf",
        owner_id=1,
    )


class TestPDFService:
    """Test cases for PDF service functions."""

    @pytest.fixture(autouse=True)
    def setup(self, pdf_service, tmp_path, monkeypatch):
        """Set up test environment before each test."""
        self.test_dir = tmp_path
        self.pdf_service = pdf_service

        # Store the original temp_dir to restore it later
        self.original_temp_dir = getattr(self.pdf_service, "temp_dir", None)

        # Create a test upload folder
        self.upload_folder = self.test_dir / "uploads"
        self.upload_folder.mkdir()

        # Patch the settings.UPLOAD_FOLDER to use our test directory
        from app.core import config

        monkeypatch.setattr(
            config.settings, "UPLOAD_FOLDER", self.upload_folder
        )

        # Set the temp directory for the PDFService
        self.pdf_service.temp_dir = self.test_dir / "temp"
        self.pdf_service.temp_dir.mkdir(exist_ok=True)

        self.test_files = []

        # Create a test file in the temporary directory
        test_file = self.test_dir / "test.png"
        test_file.write_bytes(b"test image content")
        self.test_files.append(test_file)

        # Create a test image
        self.test_image = self.test_dir / "test.png"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(self.test_image, "PNG")

        # Create a test PDF
        self.test_pdf = self.test_dir / "test.pdf"
        with open(self.test_pdf, "wb") as f:
            f.write(img2pdf.convert([self.test_image]))

        yield

        # Cleanup - restore the original temp_dir
        if (
            hasattr(self, "original_temp_dir")
            and self.original_temp_dir is not None
        ):
            self.pdf_service.temp_dir = self.original_temp_dir
        else:
            # If there was no original temp_dir, clean up the test one
            if hasattr(self, "test_dir") and self.test_dir.exists():
                shutil.rmtree(self.test_dir, ignore_errors=True)

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
            owner_id=1,  # This should match the owner_id used in the test (1)
        )
        return file

    @patch("app.services.pdf_service.os.makedirs")
    @patch("pathlib.Path.exists", return_value=False)
    @patch("app.services.pdf_service.crud.file.create")
    @patch("img2pdf.convert")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("app.services.pdf_service.File")
    def test_convert_image_to_pdf_success(
        self,
        mock_file_model,
        mock_open,
        mock_convert,
        mock_crud_create,
        mock_exists,
        mock_makedirs,
        mock_db,
        mock_file,
    ):
        """Test successful image to PDF conversion with all external calls mocked."""
        # Setup test data
        file_id = 1
        owner_id = 1

        # Mock the SQLAlchemy query
        query_mock = MagicMock()
        filter_mock = MagicMock()
        first_mock = MagicMock(return_value=mock_file)
        filter_mock.first = first_mock
        query_mock.filter.return_value = filter_mock
        mock_db.query.return_value = query_mock

        # Mock the PDF content
        pdf_content = b"%PDF-1.4 test pdf content"
        mock_convert.return_value = pdf_content

        # Mock the created file
        created_file = MagicMock()
        created_file.id = 2
        created_file.filename = "test.pdf"
        created_file.content_type = "application/pdf"
        created_file.owner_id = owner_id
        mock_crud_create.return_value = created_file

        # Mock file handles
        mock_file_handle = MagicMock()
        mock_file_handle.__enter__.return_value = mock_file_handle
        mock_file_handle.read.return_value = b"mock image content"

        mock_output_handle = MagicMock()
        mock_output_handle.__enter__.return_value = mock_output_handle

        # Configure open() to return the appropriate handle
        def open_side_effect(filename, mode="r", **kwargs):
            if isinstance(filename, Path):
                filename = str(filename)
            if "w" in mode or "wb" in mode:
                return mock_output_handle
            return mock_file_handle

        mock_open.side_effect = open_side_effect

        # Test the function
        result = self.pdf_service.convert_image_to_pdf(
            mock_db, file_id, owner_id
        )

        # Verify the result
        assert result is not None
        assert result.id == 2
        assert result.filename == "test.pdf"
        assert result.content_type == "application/pdf"
        assert result.owner_id == owner_id

        # Verify the mocks were called correctly
        mock_db.query.assert_called_once_with(mock_file_model)
        query_mock.filter.assert_called_once()
        mock_convert.assert_called_once()
        mock_crud_create.assert_called_once()

        # Verify the output file was written to
        mock_output_handle.write.assert_called_once_with(pdf_content)

    def test_convert_image_to_pdf_file_not_found(self, mock_db):
        """Test image to PDF conversion with non-existent file."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = (
            None
        )
        mock_db.query.return_value.filter.return_value.first.return_value = (
            None
        )

        # Test & Verify
        with pytest.raises(ValueError, match="File with id 999 not found"):
            self.pdf_service.convert_image_to_pdf(mock_db, 999, 1)

    @patch("builtins.open", new_callable=MagicMock)
    @patch("img2pdf.convert")
    def test_convert_image_to_pdf_conversion_error(
        self, mock_convert, mock_open, mock_db, mock_file, tmp_path
    ):
        """Test image to PDF conversion with conversion error."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_file
        )

        # Set the temp directory for the PDFService instance
        self.pdf_service.temp_dir = tmp_path

        # Setup mock file for input
        mock_file_handle = MagicMock()
        mock_file_handle.__enter__.return_value = mock_file_handle
        mock_file_handle.read.return_value = b"test image content"

        # Create separate mock for output file (should not be used)
        mock_output_handle = MagicMock()
        mock_output_handle.__enter__.return_value = mock_output_handle

        # Side effect to return different mocks for input and output files
        def open_side_effect(filename, mode="r"):
            if "rb" in mode:
                return mock_file_handle
            return mock_output_handle

        mock_open.side_effect = open_side_effect

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
            self.pdf_service.convert_image_to_pdf(mock_db, 1, 1)

        # Check the error message
        assert "Failed to convert image to PDF" in str(exc_info.value)
        assert "Invalid image" in str(exc_info.value)

        # Verify no database operations were performed
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()

        # Verify file operations
        mock_file_handle.read.assert_called_once()
        mock_output_handle.write.assert_not_called()

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
        mock_file1.owner_id = (
            1  # This should match the owner_id passed to merge_pdfs
        )

        mock_file2 = MagicMock()
        mock_file2.id = 2
        mock_file2.filename = "test2.pdf"
        mock_file2.filepath = str(pdf2_path)
        mock_file2.content_type = "application/pdf"
        mock_file2.owner_id = (
            1  # This should match the owner_id passed to merge_pdfs
        )

        # Mock the crud.file.get method to return our mock files
        def mock_file_get(db, id):
            if id == 1:
                return mock_file1
            elif id == 2:
                return mock_file2
            return None

        # Setup mock settings
        output_dir = test_dir / "output"
        output_dir.mkdir()
        mock_settings.UPLOAD_FOLDER = test_dir

        # Set the temp directory for the PDFService instance
        self.pdf_service.temp_dir = output_dir

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

        # Patch the crud.file.get method and run the test
        with patch(
            "app.services.pdf_service.crud.file.get", side_effect=mock_file_get
        ):
            # Test using the PDFService instance
            result = self.pdf_service.merge_pdfs(
                mock_db, [1, 2], "merged.pdf", 1
            )

            # Verify
            assert result is not None
            assert result.id == 3
            assert result.filename == "merged.pdf"
            assert result.content_type == "application/pdf"

            # Verify the merged file was created with expected content
            # The actual output path should be in the TEMP_DIR with the given output filename
            assert (
                actual_output_path is not None
            ), "Output file path was not set"
            assert os.path.exists(
                actual_output_path
            ), f"Output file not found at {actual_output_path}"
            assert (
                os.path.getsize(actual_output_path) > 0
            ), "Output file is empty"

            # Verify the merged PDF contains the expected number of pages (2)
            with open(actual_output_path, "rb") as f:
                reader = PdfReader(f)
                assert (
                    len(reader.pages) == 2
                ), f"Expected 2 pages, got {len(reader.pages)}"

        # The returned file object should have the same path as the actual output
        assert result.filepath == actual_output_path

    def test_merge_pdfs_file_not_found(self, mock_db, mock_pdf_file):
        """Test merging with non-existent file raises error."""

        # Setup - mock the crud.file.get method to return None for non-existent files
        def mock_file_get(db, id):
            if id == 1:
                return mock_pdf_file
            return None  # Simulate file not found

        # Test & Verify
        with patch(
            "app.services.pdf_service.crud.file.get", side_effect=mock_file_get
        ):
            with pytest.raises(ValueError) as exc_info:
                self.pdf_service.merge_pdfs(mock_db, [1, 999], "output.pdf", 1)

            # Check that the error message contains the missing ID
            assert "File with ID 999 not found" in str(exc_info.value)

    def test_merge_pdfs_empty_list(self, mock_db):
        """Test merging with empty file_ids list raises error."""
        # Test & Verify
        with pytest.raises(ValueError) as exc_info:
            self.pdf_service.merge_pdfs(mock_db, [], "output.pdf", 1)

        # Check the error message
        assert "No files provided to merge" in str(exc_info.value)

    @patch("builtins.open", new_callable=MagicMock)
    @patch("img2pdf.convert")
    def test_convert_image_to_pdf_image_open_error(
        self, mock_convert, mock_open, mock_db, mock_file, caplog
    ):
        """Test ImageOpenError during image to PDF conversion."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_file
        )

        # Mock the PDF conversion to raise ImageOpenError
        mock_convert.side_effect = img2pdf.ImageOpenError(
            "Invalid image format"
        )

        # Test & Verify
        with pytest.raises(ValueError) as exc_info:
            self.pdf_service.convert_image_to_pdf(mock_db, 1, 1)

        # Check the error message
        assert "Failed to convert image to PDF" in str(exc_info.value)
        assert "Invalid image format" in str(exc_info.value)

        # Verify no database operations were performed
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()

        # No error log should be recorded for ImageOpenError as it's converted to ValueError
        assert "Unexpected error during PDF conversion" not in caplog.text

    @patch("builtins.open")
    @patch("img2pdf.convert")
    def test_convert_image_to_pdf_file_operation_error(
        self, mock_convert, mock_open, mock_db, mock_file, caplog
    ):
        """Test file operation error during PDF saving."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_file
        )

        # Mock the PDF conversion to succeed
        mock_convert.return_value = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/Parent 2 0 R/Resources<<>>/MediaBox[0 0 612 792]>>\nendobj\n"

        # Mock file open to raise OSError when saving the PDF
        mock_open.side_effect = OSError("Disk full")

        # Test & Verify
        with pytest.raises(ValueError) as exc_info:
            self.pdf_service.convert_image_to_pdf(mock_db, 1, 1)

        # Check the error message
        assert "Failed to process file: Disk full" in str(exc_info.value)

        # Check logs
        assert "File operation error: Disk full" in caplog.text

        # Verify no database operations were performed
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()

    @patch("builtins.open", new_callable=MagicMock)
    @patch("pypdf.PdfReader")
    def test_merge_pdfs_invalid_pdf(
        self, mock_reader_class, mock_open, mock_db, mock_pdf_file
    ):
        """Test merging with invalid PDF raises error."""
        # Create a second mock PDF file with the same owner
        mock_pdf_file_2 = MagicMock()
        mock_pdf_file_2.id = 2
        mock_pdf_file_2.filename = "test2.pdf"
        mock_pdf_file_2.filepath = "/path/to/test2.pdf"
        mock_pdf_file_2.content_type = "application/pdf"
        mock_pdf_file_2.owner_id = 1  # Same owner as the first file

        # Setup mock for crud.file.get
        def mock_file_get(db, id):
            if id == 1:
                return mock_pdf_file
            elif id == 2:
                return mock_pdf_file_2
            return None

        # Setup mock_open to provide file content
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
                # Second file raises error when trying to read it
                raise Exception("Invalid PDF")

        mock_open.side_effect = open_side_effect

        # Mock PdfReader to raise an error for the second file
        def pdf_reader_side_effect(*args, **kwargs):
            if not hasattr(pdf_reader_side_effect, "call_count"):
                pdf_reader_side_effect.call_count = 0

            pdf_reader_side_effect.call_count += 1

            if pdf_reader_side_effect.call_count == 1:
                # First file is valid
                mock_reader = MagicMock()
                mock_reader.pages = [MagicMock()]
                return mock_reader
            else:
                # Second file raises error
                raise Exception("Invalid PDF")

        mock_reader_class.side_effect = pdf_reader_side_effect

        # Test & Verify
        with patch(
            "app.services.pdf_service.crud.file.get", side_effect=mock_file_get
        ):
            with pytest.raises(ValueError, match="Error reading file 2"):
                self.pdf_service.merge_pdfs(
                    mock_db,
                    [1, 2],
                    "output.pdf",
                    1,  # owner_id=1 matches the mock files
                )

        # Verify no database operations were performed
        mock_db.add.assert_not_called()

    @patch("pypdf.PdfWriter")
    @patch("pypdf.PdfReader")
    @patch("builtins.open")
    @patch("os.makedirs")
    @patch("os.path.exists", return_value=True)
    @patch("os.access", return_value=True)
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

        # Setup test data
        file_ids = [1, 2]
        output_filename = "output.pdf"
        owner_id = 1

        # Use the provided mock DB session
        db = mock_db

        # Track all open calls
        open_calls = []

        # Create a temporary directory for test files
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temporary input files
            input1 = Path(temp_dir) / "input1.pdf"
            input1.touch()
            input2 = Path(temp_dir) / "input2.pdf"
            input2.touch()

            # Setup mocks
            with patch("uuid.uuid4", return_value="test-uuid"), patch(
                "app.services.pdf_service.crud.file.get"
            ) as mock_get_file, patch(
                "app.services.pdf_service.crud.file.create"
            ) as mock_create_file, patch(
                "app.services.pdf_service.settings.UPLOAD_FOLDER",
                Path(temp_dir),
            ):

                # Setup mock for file existence
                def exists_side_effect(path):
                    path_str = str(path)
                    return path_str in (str(input1), str(input2))

                mock_exists.side_effect = exists_side_effect

                # Setup mock for file retrieval
                mock_pdf_file1 = MagicMock()
                mock_pdf_file1.id = 1
                mock_pdf_file1.filepath = str(input1)
                mock_pdf_file1.owner_id = owner_id

                mock_pdf_file2 = MagicMock()
                mock_pdf_file2.id = 2
                mock_pdf_file2.filepath = str(input2)
                mock_pdf_file2.owner_id = owner_id

                def get_file_side_effect(db, id):
                    if id == 1:
                        return mock_pdf_file1
                    elif id == 2:
                        return mock_pdf_file2
                    return None

                mock_get_file.side_effect = get_file_side_effect

                # Setup mock for PdfReader that simulates a valid PDF
                class MockPdfReader:
                    def __init__(self, *args, **kwargs):
                        self.pages = [MagicMock()]  # One mock page
                        self.stream = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000102 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n149\n%%EOF\n"

                mock_reader_class.side_effect = MockPdfReader

                # Setup mock for PdfWriter with required methods
                mock_writer = MagicMock()
                mock_writer.append = MagicMock()
                mock_writer.write = MagicMock()
                mock_writer_class.return_value = mock_writer

                # Mock the PdfMerger to avoid actual file operations
                with patch(
                    "app.services.pdf_service.PdfWriter",
                    return_value=mock_writer,
                ) as mock_merger_class:
                    # Mock the open function
                    def open_side_effect(filename, mode="rb", **kwargs):
                        filename_str = str(filename)
                        open_calls.append((filename_str, mode, kwargs))
                        logger.debug(
                            f"open() called with filename: {filename_str}, mode: {mode}"
                        )

                        # For output file, raise PermissionError
                        if "output" in filename_str and (
                            "w" in mode or "wb" in mode
                        ):
                            logger.debug(
                                "Raising PermissionError for output file"
                            )
                            raise PermissionError("Permission denied")

                        # For input files, return a file-like object
                        logger.debug("Returning file handle for input file")
                        return open(filename, mode, **kwargs)

                    mock_open.side_effect = open_side_effect

                    # Test & Verify
                    with pytest.raises(ValueError) as exc_info:
                        logger.debug("Calling merge_pdfs")
                        result = self.pdf_service.merge_pdfs(
                            db=db,
                            file_ids=file_ids,
                            output_filename=output_filename,
                            owner_id=owner_id,
                        )

                    # Verify the error message
                    assert "Permission denied" in str(exc_info.value)

                    # Verify file operations were attempted
                    assert (
                        len(open_calls) > 0
                    ), "No file operations were attempted"

                    # Verify that we tried to open the output file for writing
                    output_opened = any(
                        "output.pdf" in call[0]
                        and ("w" in call[1] or "wb" in call[1])
                        for call in open_calls
                    )
                    assert (
                        output_opened
                    ), "Expected to attempt opening output file in write mode"

                    # Verify PdfWriter was called and methods were called as expected
                    mock_merger_class.assert_called_once()
                    # Verify append was called for each input file
                    assert mock_writer.append.call_count == len(file_ids)
                    # Verify write was not called due to permission error
                    mock_writer.write.assert_not_called()

                    # Verify no database operations were performed
                    mock_db.commit.assert_not_called()
                    mock_db.refresh.assert_not_called()

                    logger.debug("Test completed successfully")

        logger.debug("Test completed")
