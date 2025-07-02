"""Tests for PDF generation API endpoints."""

import io
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.models.file import File as FileModel


class TestPDFEndpoints:
    """Test PDF generation and manipulation endpoints."""

    @pytest.fixture
    def test_image(self) -> bytes:
        """Generate a test image for PDF generation tests."""
        img = Image.new("RGB", (100, 100), color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @pytest.fixture
    def uploaded_files(
        self, authorized_client: TestClient, test_image: bytes
    ) -> Dict[str, Any]:
        """Upload test files and return their IDs."""
        files = []
        for i in range(3):
            response = authorized_client.post(
                "/api/v1/files/upload/",
                files={"file": (f"test_{i}.png", test_image, "image/png")},
            )
            assert response.status_code == 200
            files.append(response.json())
        return {"files": files, "file_ids": [f["id"] for f in files]}

    def test_convert_image_to_pdf(
        self,
        authorized_client: TestClient,
        test_image: bytes,
        db_session: Session,
    ) -> None:
        """Test converting an uploaded image to PDF."""
        # Upload an image
        response = authorized_client.post(
            "/api/v1/files/upload/",
            files={"file": ("test.png", test_image, "image/png")},
        )
        assert response.status_code == 200
        file_data = response.json()

        # Convert to PDF
        response = authorized_client.post(
            f"/api/v1/files/{file_data['id']}/convert-to-pdf/"
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "file_id" in data

        # Verify the PDF file was created
        pdf_file = db_session.query(FileModel).get(data["file_id"])
        assert pdf_file is not None
        assert pdf_file.content_type == "application/pdf"
        assert pdf_file.filename.endswith(".pdf")
        assert Path(pdf_file.filepath).exists()

    def test_merge_pdfs(
        self,
        authorized_client: TestClient,
        uploaded_files: Dict[str, Any],
        db_session: Session,
    ) -> None:
        """Test merging multiple PDFs."""
        # First, convert all images to PDFs
        pdf_file_ids = []
        for file_id in uploaded_files["file_ids"]:
            response = authorized_client.post(
                f"/api/v1/files/{file_id}/convert-to-pdf/"
            )
            assert response.status_code == 200
            pdf_file_ids.append(response.json()["file_id"])

        # Merge the PDFs
        response = authorized_client.post(
            "/api/v1/files/merge-pdfs/",
            json={"file_ids": pdf_file_ids},
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "file_id" in data

        # Verify the merged PDF was created
        merged_file = db_session.query(FileModel).get(data["file_id"])
        assert merged_file is not None
        assert merged_file.content_type == "application/pdf"
        assert "merged_" in merged_file.filename
        assert Path(merged_file.filepath).exists()

    def test_merge_pdfs_invalid_file(
        self, authorized_client: TestClient, test_file: FileModel
    ) -> None:
        """Test merging with an invalid file type."""
        # Try to merge with a non-PDF file
        response = authorized_client.post(
            "/api/v1/files/merge-pdfs/",
            json={"file_ids": [test_file.id]},
        )

        assert response.status_code == 400
        assert "All files must be PDFs" in response.json()["detail"]

    def test_merge_pdfs_insufficient_files(
        self, authorized_client: TestClient
    ) -> None:
        """Test merging with insufficient number of files."""
        # Try to merge with less than 2 files
        response = authorized_client.post(
            "/api/v1/files/merge-pdfs/",
            json={"file_ids": []},
        )

        assert response.status_code == 400
        assert "At least two files are required" in response.json()["detail"]

    def test_download_pdf(
        self, authorized_client: TestClient, uploaded_files: Dict[str, Any]
    ) -> None:
        """Test downloading a generated PDF."""
        # First, convert an image to PDF
        response = authorized_client.post(
            f"/api/v1/files/{uploaded_files['file_ids'][0]}/convert-to-pdf/"
        )
        assert response.status_code == 200
        pdf_file_id = response.json()["file_id"]

        # Download the PDF
        response = authorized_client.get(
            f"/api/v1/files/{pdf_file_id}/download"
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]

    def test_pdf_metadata(
        self, authorized_client: TestClient, uploaded_files: Dict[str, Any]
    ) -> None:
        """Test retrieving PDF metadata."""
        # First, convert an image to PDF
        response = authorized_client.post(
            f"/api/v1/files/{uploaded_files['file_ids'][0]}/convert-to-pdf/"
        )
        assert response.status_code == 200
        pdf_file_id = response.json()["file_id"]

        # Get file metadata
        response = authorized_client.get(f"/api/v1/files/{pdf_file_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pdf_file_id
        assert data["content_type"] == "application/pdf"
        assert data["filename"].endswith(".pdf")
        assert data["size"] > 0
