"""Tests for PDF generation functionality."""

import io
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from PIL import Image

import img2pdf
from app.core.pdf_generator import PDFGenerator


class TestPDFGenerator:
    """Test PDF generation functionality."""

    @pytest.fixture
    def test_image(self) -> bytes:
        """Generate a test image for PDF generation tests."""
        img = Image.new("RGB", (100, 100), color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @pytest.fixture
    def test_pdf(self) -> bytes:
        """Generate a simple PDF file for testing."""
        # This is a minimal PDF file with a single blank page
        return (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] >>\nendobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000015 00000 n \n0000000060 00000 n \n0000000116 00000 n \n"
            b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
        )

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("img2pdf.convert")
    def test_image_to_pdf_with_bytes(
        self,
        mock_convert: MagicMock,
        mock_file: MagicMock,
        mock_mkdir: MagicMock,
        test_image: bytes,
    ) -> None:
        """Test converting image bytes to PDF."""
        # Setup
        output_path = Path("/tmp/output.pdf")
        mock_convert.return_value = b"dummy_pdf_content"

        # Test
        result = PDFGenerator.image_to_pdf(test_image, output_path)

        # Verify
        assert result == output_path
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_convert.assert_called_once_with(test_image)
        mock_file().write.assert_called_once_with(b"dummy_pdf_content")

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("img2pdf.convert")
    def test_image_to_pdf_with_file_object(
        self,
        mock_convert: MagicMock,
        mock_file: MagicMock,
        mock_mkdir: MagicMock,
        test_image: bytes,
    ) -> None:
        """Test converting image file object to PDF."""
        # Setup
        output_path = Path("/tmp/output.pdf")
        mock_convert.return_value = b"dummy_pdf_content"

        # Create a mock for the file object that will be passed to convert
        mock_file_obj = MagicMock()
        mock_file_obj.read.return_value = test_image
        # Configure tell() to return 0 to simulate file at start position
        mock_file_obj.tell.return_value = 0
        # Configure seek() to do nothing
        mock_file_obj.seek = MagicMock()

        # Test with the mock file object
        result = PDFGenerator.image_to_pdf(mock_file_obj, output_path)

        # Verify
        assert result == output_path
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_convert.assert_called_once()
        mock_file_obj.read.assert_called_once()
        mock_file().write.assert_called_once_with(b"dummy_pdf_content")

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("img2pdf.convert")
    def test_image_to_pdf_conversion_error(
        self,
        mock_convert: MagicMock,
        mock_file: MagicMock,
        mock_mkdir: MagicMock,
    ) -> None:
        """Test handling of image conversion errors with a file-like object."""
        # Setup
        output_path = Path("/tmp/output.pdf")

        # Create a file-like object for testing
        file_like = io.BytesIO(b"invalid image data")

        # Create a proper ImageOpenError with the expected attributes
        error = img2pdf.ImageOpenError("Invalid image data")
        error.message = "Invalid image data"
        mock_convert.side_effect = error

        # Test & Verify
        with pytest.raises(
            ValueError,
            match="Failed to convert image to PDF: Invalid image data",
        ):
            PDFGenerator.image_to_pdf(file_like, output_path)

        # Verify the directory was created
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        # Verify img2pdf.convert was called with the file-like object's data
        mock_convert.assert_called_once_with(b"invalid image data")
        # Verify no write was attempted since conversion failed
        mock_file().write.assert_not_called()

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("img2pdf.convert")
    def test_image_to_pdf_bytes_conversion_error(
        self,
        mock_convert: MagicMock,
        mock_file: MagicMock,
        mock_mkdir: MagicMock,
    ) -> None:
        """Test handling of image conversion errors with bytes input."""
        # Setup
        output_path = Path("/tmp/output.pdf")

        # Create test image bytes
        image_bytes = b"invalid image data"

        # Create a proper ImageOpenError with the expected attributes
        error = img2pdf.ImageOpenError("Invalid image data")
        error.message = "Invalid image data"
        mock_convert.side_effect = error

        # Test & Verify
        with pytest.raises(
            ValueError,
            match="Failed to convert image to PDF: Invalid image data",
        ):
            PDFGenerator.image_to_pdf(image_bytes, output_path)

        # Verify the directory was created
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        # Verify img2pdf.convert was called with the image bytes
        mock_convert.assert_called_once_with(image_bytes)
        # Verify no write was attempted since conversion failed
        mock_file().write.assert_not_called()

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open")
    @patch("img2pdf.convert")
    def test_image_to_pdf_write_error(
        self,
        mock_convert: MagicMock,
        mock_open_func: MagicMock,
        mock_mkdir: MagicMock,
        test_image: bytes,
    ) -> None:
        """Test handling of file write errors."""
        # Setup
        output_path = Path("/tmp/output.pdf")
        mock_convert.return_value = b"dummy_pdf_content"

        # Mock the file object that open() returns
        mock_file = MagicMock()
        mock_file.__enter__.return_value.write.side_effect = IOError(
            "Disk full"
        )
        mock_open_func.return_value = mock_file

        # Test & Verify
        with pytest.raises(
            ValueError, match="Failed to convert image to PDF: Disk full"
        ):
            PDFGenerator.image_to_pdf(test_image, output_path)

        mock_convert.assert_called_once()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_create_blank_page_default_dimensions(self) -> None:
        """Test creating a blank page with default dimensions."""
        # Act
        pdf_data = PDFGenerator.create_blank_page()

        # Assert
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 0
        assert b"%PDF" in pdf_data  # PDF header

    def test_create_blank_page_custom_dimensions(self) -> None:
        """Test creating a blank page with custom dimensions."""
        # Act
        width, height = 300, 400  # 4.17" x 5.56" at 72 DPI
        pdf_data = PDFGenerator.create_blank_page(width=width, height=height)

        # Assert
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 0
        assert b"%PDF" in pdf_data  # PDF header

    def test_create_blank_page_invalid_dimensions(self) -> None:
        """Test creating a blank page with invalid dimensions."""
        # Test with zero width
        with pytest.raises(ValueError):
            PDFGenerator.create_blank_page(width=0, height=100)

        # Test with zero height
        with pytest.raises(ValueError):
            PDFGenerator.create_blank_page(width=100, height=0)

        # Test with negative dimensions
        with pytest.raises(ValueError):
            PDFGenerator.create_blank_page(width=-100, height=100)

        with pytest.raises(ValueError):
            PDFGenerator.create_blank_page(width=100, height=-100)

    def test_merge_pdfs_success(self, tmp_path: Path) -> None:
        """Test merging multiple PDFs successfully by verifying the output PDF."""
        # Create two simple PDFs with distinct content
        pdf1_path = tmp_path / "test1.pdf"
        pdf2_path = tmp_path / "test2.pdf"
        output_path = tmp_path / "merged.pdf"

        # Create first PDF with content "PDF 1"
        with open(pdf1_path, "wb") as f:
            f.write(
                b"%PDF-1.4\n"
                b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
                b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
                b"3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >> endobj\n"
                b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
                b"5 0 obj << /Length 44 >> stream\n"
                b"BT /F1 24 Tf 100 700 Td (PDF 1) Tj ET\n"
                b"endstream endobj\n"
                b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000145 00000 n \n0000000221 00000 n \n0000000274 00000 n \n"
                b"trailer << /Size 6 /Root 1 0 R >>\n"
                b"startxref\n400\n"
                b"%%EOF\n"
            )

        # Create second PDF with content "PDF 2"
        with open(pdf2_path, "wb") as f:
            f.write(
                b"%PDF-1.4\n"
                b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
                b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
                b"3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >> endobj\n"
                b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
                b"5 0 obj << /Length 44 >> stream\n"
                b"BT /F1 24 Tf 100 600 Td (PDF 2) Tj ET\n"
                b"endstream endobj\n"
                b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000145 00000 n \n0000000221 00000 n \n0000000274 00000 n \n"
                b"trailer << /Size 6 /Root 1 0 R >>\n"
                b"startxref\n400\n"
                b"%%EOF\n"
            )

        # Test merging the two PDFs
        result = PDFGenerator.merge_pdfs([pdf1_path, pdf2_path], output_path)

        # Verify the result path is correct
        assert result == output_path

        # Verify the output file was created
        assert output_path.exists()

        # Verify the output file is not empty
        assert output_path.stat().st_size > 0

        # Verify the output contains content from both PDFs
        with open(output_path, "rb") as f:
            content = f.read()
            assert b"PDF 1" in content
            assert b"PDF 2" in content

    @patch("pypdf.PdfWriter")
    def test_merge_pdfs_empty_list(
        self, mock_writer_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test merging with an empty list of PDFs raises ValueError."""
        output_path = tmp_path / "merged.pdf"

        with pytest.raises(ValueError, match="No PDF files to merge"):
            PDFGenerator.merge_pdfs([], output_path)

        # Verify no writer was created or used
        mock_writer_class.assert_not_called()
        # close() should not be called since writer is never created
        if hasattr(mock_writer_class.return_value, "close"):
            mock_writer_class.return_value.close.assert_not_called()

    @patch("pypdf.PdfWriter")
    @patch("pypdf.PdfReader")
    def test_merge_pdfs_file_not_found(
        self,
        mock_reader_class: MagicMock,
        mock_writer_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test merging with non-existent PDF files raises FileNotFoundError."""
        non_existent_path = tmp_path / "nonexistent.pdf"
        output_path = tmp_path / "merged.pdf"

        with pytest.raises(FileNotFoundError):
            PDFGenerator.merge_pdfs([non_existent_path], output_path)

        # Verify PdfReader was not called since the file doesn't exist
        mock_reader_class.assert_not_called()

    def test_create_blank_page(self) -> None:
        """Test creating a blank PDF page."""
        # Test with default dimensions
        result = PDFGenerator.create_blank_page()
        assert isinstance(result, bytes)
        assert len(result) > 0

        # Test with custom dimensions
        custom_result = PDFGenerator.create_blank_page(300, 400)
        assert isinstance(custom_result, bytes)
        assert len(custom_result) > 0
        assert (
            custom_result != result
        )  # Different dimensions should produce different outputs

    def test_merge_pdfs_file_not_found(self, tmp_path: Path) -> None:
        """Test merging PDFs when a file is not found."""
        # Create a non-existent file path
        non_existent_file = tmp_path / "nonexistent.pdf"
        output_path = tmp_path / "merged.pdf"

        # Test with a non-existent file
        with pytest.raises(FileNotFoundError) as exc_info:
            PDFGenerator.merge_pdfs([non_existent_file], output_path)

        # Verify the error message contains the missing file path
        assert str(non_existent_file) in str(exc_info.value)

    def test_image_to_pdf_with_file_object_not_at_start(
        self, tmp_path: Path
    ) -> None:
        """Test converting image file object to PDF when file pointer is not at start."""
        # Setup
        output_path = tmp_path / "output.pdf"

        # Create a test image file
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path, format="PNG")

        # Create a mock file object that tracks seek/tell
        mock_file = MagicMock()
        mock_file.read.return_value = b"test image data"
        mock_file.tell.return_value = (
            10  # Simulate file pointer at position 10
        )

        # Mock img2pdf.convert to return a valid PDF
        with patch(
            "img2pdf.convert",
            return_value=b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Parent 2 0 R/Contents 5 0 R>>endobj\n4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n5 0 obj<</Length 44>>stream\nBT/F1 24 Tf 100 700 Td (Hello, World!) Tj ET\nendstream endobj\nxref\n0 6\n0000000000 65535 f \n0000000015 00000 n \n0000000074 00000 n \n0000000145 00000 n \n0000000221 00000 n \n0000000274 00000 n \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n400\n%%EOF",
        ):
            # Test with the mock file object
            result = PDFGenerator.image_to_pdf(mock_file, output_path)

            # Verify the file pointer was reset to the start
            mock_file.seek.assert_called_once_with(0)

        # Verify the output file was created and is not empty
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_image_to_pdf_with_invalid_image(self, tmp_path: Path) -> None:
        """Test converting an invalid image to PDF."""
        # Setup
        output_path = tmp_path / "output.pdf"

        # Create a file with invalid image data
        invalid_image_data = b"not a valid image"

        # Test with invalid image data
        with patch(
            "builtins.open", mock_open(read_data=invalid_image_data)
        ) as mock_file:
            with patch(
                "img2pdf.convert",
                side_effect=img2pdf.ImageOpenError("Invalid image data"),
            ) as mock_convert:
                with pytest.raises(ValueError) as exc_info:
                    PDFGenerator.image_to_pdf(invalid_image_data, output_path)

                # Verify the error message is as expected
                assert "Failed to convert image to PDF" in str(exc_info.value)

                # Verify img2pdf.convert was called with the image data
                mock_convert.assert_called_once_with(invalid_image_data)

                # Verify the output file was not written to
                assert not output_path.exists()

    def test_image_to_pdf_unexpected_error(self, tmp_path: Path) -> None:
        """Test handling of unexpected errors during PDF conversion."""
        # Setup
        output_path = tmp_path / "output.pdf"
        test_data = b"test image data"

        # Create a mock file object
        mock_file = MagicMock()
        mock_file.read.return_value = test_data

        # Mock the open function to return our mock file
        with patch("builtins.open", mock_open()) as mock_file_open:
            # Mock img2pdf.convert to raise an unexpected exception
            with patch(
                "img2pdf.convert", side_effect=RuntimeError("Unexpected error")
            ) as mock_convert:
                with pytest.raises(ValueError) as exc_info:
                    PDFGenerator.image_to_pdf(test_data, output_path)

                # Verify the error message is as expected
                assert (
                    "Failed to convert image to PDF: Unexpected error"
                    in str(exc_info.value)
                )

                # Verify the file was opened in write binary mode
                mock_file_open.assert_called_once_with(output_path, "wb")

                # Verify the output file was not left in a bad state
                assert not output_path.exists()

    def test_image_to_pdf_io_error(self, tmp_path: Path) -> None:
        """Test handling of IOError when writing the PDF file."""
        # Setup
        output_path = tmp_path / "output.pdf"
        test_data = b"test image data"

        # Create a mock that will raise IOError when writing
        mock_file = MagicMock()
        mock_file.__enter__.return_value.write.side_effect = IOError(
            "Disk full"
        )

        # Mock the open function to return our mock file
        with patch("builtins.open", return_value=mock_file):
            # Mock img2pdf.convert to return some data
            with patch("img2pdf.convert", return_value=b"%PDF-1.4\nDummy PDF"):
                with pytest.raises(ValueError) as exc_info:
                    PDFGenerator.image_to_pdf(test_data, output_path)

                # Verify the error message is as expected
                assert "Failed to convert image to PDF: Disk full" in str(
                    exc_info.value
                )

                # Verify the file was attempted to be written to
                mock_file.__enter__.return_value.write.assert_called_once()

    def test_image_to_pdf_permission_denied(self, tmp_path: Path) -> None:
        """Test handling of PermissionError when writing to a read-only directory."""
        # Setup
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o444)  # Make directory read-only

        try:
            output_path = read_only_dir / "output.pdf"
            test_data = b"test image data"

            with pytest.raises(IOError) as exc_info:
                PDFGenerator.image_to_pdf(test_data, output_path)

            # Verify the error message is as expected
            assert "Failed to write PDF file: " in str(exc_info.value)
            assert "Permission denied" in str(exc_info.value)
        finally:
            # Clean up - make directory writable again so it can be removed
            read_only_dir.chmod(0o777)

    def test_image_to_pdf_file_like_no_seek_tell(self, tmp_path: Path) -> None:
        """Test image_to_pdf with a file-like object that doesn't support seek/tell."""
        # Setup
        output_path = tmp_path / "output.pdf"

        # Create a simple file-like object without seek/tell methods
        class SimpleFile:
            def read(self):
                return b"test image data"

        # Mock img2pdf.convert to return a valid PDF
        with patch("img2pdf.convert", return_value=b"%PDF-1.4\nDummy PDF"):
            result = PDFGenerator.image_to_pdf(SimpleFile(), output_path)

            # Verify the result is the output path
            assert result == output_path

            # Verify the file was written
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    @patch("PIL.Image.new")
    @patch("PIL.Image.Image.save")
    def test_create_blank_page(
        self, mock_save: MagicMock, mock_new: MagicMock
    ) -> None:
        """Test creating a blank PDF page."""
        # Setup
        mock_img = MagicMock()
        mock_new.return_value = mock_img

        # Create a mock BytesIO object for the image data
        mock_byte_arr = MagicMock()
        mock_byte_arr.getvalue.return_value = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Parent 2 0 R/Contents 5 0 R>>endobj\n4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n5 0 obj<</Length 44>>stream\nBT/F1 24 Tf 100 700 Td (Hello, World!) Tj ET\nendstream endobj\nxref\n0 6\n0000000000 65535 f \n0000000015 00000 n \n0000000074 00000 n \n0000000145 00000 n \n0000000221 00000 n \n0000000274 00000 n \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n400\n%%EOF"

        # Mock the BytesIO constructor to return our mock
        with patch("io.BytesIO", return_value=mock_byte_arr) as mock_bytes_io:
            # Test with default dimensions
            result = PDFGenerator.create_blank_page()

            # Verify the result is the expected PDF data
            assert isinstance(result, bytes)
            assert result.startswith(b"%PDF-1.4")

            # Verify the image was created with default dimensions
            mock_new.assert_called_once_with("RGB", (612, 792), color="white")

            # Verify the image was saved to the BytesIO object as PDF
            mock_img.save.assert_called_once_with(mock_byte_arr, format="PDF")

            # Verify the BytesIO was properly cleaned up
            mock_byte_arr.getvalue.assert_called_once()

        # Test with custom dimensions
        mock_new.reset_mock()
        mock_save.reset_mock()
        mock_byte_arr.getvalue.reset_mock()

        with patch("io.BytesIO", return_value=mock_byte_arr):
            # Test with custom dimensions
            result = PDFGenerator.create_blank_page(300, 400)

            # Verify the result is the expected PDF data
            assert isinstance(result, bytes)

            # Verify the image was created with custom dimensions
            mock_new.assert_called_once_with("RGB", (300, 400), color="white")
