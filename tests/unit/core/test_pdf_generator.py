"""Tests for PDF generation functionality."""
import io
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.core.pdf_generator import PDFGenerator
from app.models.file import File


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
    
    @pytest.fixture
    def test_files(self, test_image: bytes) -> List[File]:
        """Create test file objects."""
        return [
            File(
                filename=f"test_{i}.png",
                filepath=f"/tmp/test_{i}.png",
                content_type="image/png",
                size=len(test_image),
            )
            for i in range(3)
        ]
    
    def test_convert_image_to_pdf(self, tmp_path: Path, test_image: bytes) -> None:
        """Test converting an image to PDF."""
        # Create a test image file
        img_path = tmp_path / "test.png"
        with open(img_path, "wb") as f:
            f.write(test_image)
        
        # Convert to PDF
        output_path = tmp_path / "output.pdf"
        PDFGenerator.image_to_pdf(str(img_path), str(output_path))
        
        # Verify PDF was created and has content
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
        # Clean up
        output_path.unlink()
    
    def test_merge_pdfs(self, tmp_path: Path, test_pdf: bytes) -> None:
        """Test merging multiple PDFs."""
        # Create test PDF files
        pdf_paths = []
        for i in range(3):
            path = tmp_path / f"test_{i}.pdf"
            with open(path, "wb") as f:
                f.write(test_pdf)
            pdf_paths.append(str(path))
        
        # Merge PDFs
        output_path = tmp_path / "merged.pdf"
        PDFGenerator.merge_pdfs(pdf_paths, str(output_path))
        
        # Verify merged PDF was created and has content
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
        # Clean up
        output_path.unlink()
    
    @patch("app.core.pdf_generator.PDFGenerator.image_to_pdf")
    def test_process_files(self, mock_image_to_pdf: MagicMock, test_files: List[File], tmp_path: Path) -> None:
        """Test processing multiple files for PDF conversion."""
        # Set up mock
        output_paths = [str(tmp_path / f"output_{i}.pdf") for i in range(len(test_files))]
        mock_image_to_pdf.side_effect = lambda src, dst: Path(dst).touch()
        
        # Process files
        result = PDFGenerator.process_files(test_files, output_paths)
        
        # Verify results
        assert len(result) == len(test_files)
        assert all(Path(path).exists() for path in result)
        assert mock_image_to_pdf.call_count == len(test_files)
        
        # Clean up
        for path in result:
            Path(path).unlink()
    
    def test_validate_pdf(self, test_pdf: bytes, tmp_path: Path) -> None:
        """Test PDF validation."""
        # Create a test PDF file
        pdf_path = tmp_path / "test.pdf"
        with open(pdf_path, "wb") as f:
            f.write(test_pdf)
        
        # Validate PDF
        assert PDFGenerator.validate_pdf(str(pdf_path)) is True
        
        # Test with invalid PDF
        invalid_pdf_path = tmp_path / "invalid.pdf"
        with open(invalid_pdf_path, "wb") as f:
            f.write(b"Not a PDF file")
        
        assert PDFGenerator.validate_pdf(str(invalid_pdf_path)) is False
    
    def test_get_page_count(self, test_pdf: bytes, tmp_path: Path) -> None:
        """Test getting page count of a PDF."""
        # Create a test PDF file with a known number of pages
        pdf_path = tmp_path / "test.pdf"
        with open(pdf_path, "wb") as f:
            f.write(test_pdf)
        
        # Test page count
        assert PDFGenerator.get_page_count(str(pdf_path)) == 1
    
    @patch("app.core.pdf_generator.PDFGenerator.merge_pdfs")
    def test_merge_pdf_files(self, mock_merge_pdfs: MagicMock, test_files: List[File], tmp_path: Path) -> None:
        """Test merging multiple PDF files."""
        # Set up test
        output_path = str(tmp_path / "merged.pdf")
        
        # Call the method
        PDFGenerator.merge_pdf_files(test_files, output_path)
        
        # Verify merge_pdfs was called with correct arguments
        mock_merge_pdfs.assert_called_once()
        called_paths = mock_merge_pdfs.call_args[0][0]
        assert len(called_paths) == len(test_files)
        assert all(isinstance(path, str) for path in called_paths)
