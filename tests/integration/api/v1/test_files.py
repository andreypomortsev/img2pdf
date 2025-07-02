"""Tests for file operations API endpoints."""

import io
from pathlib import Path
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.file import File as FileModel


class TestFile(BaseModel):
    """Test file model for file operation testing."""

    filename: str
    content: bytes
    content_type: str
    size: int

    @classmethod
    def create_test_image(
        cls, width: int = 100, height: int = 100, color: str = "black"
    ) -> "TestFile":
        """Create a test image file."""
        img = Image.new("RGB", (width, height), color=color)
        draw = ImageDraw.Draw(img)
        # Add some content to make the file non-empty
        draw.rectangle([10, 10, width - 10, height - 10], outline="red")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        content = buf.getvalue()

        return cls(
            filename=f"test_image_{width}x{height}.png",
            content=content,
            content_type="image/png",
            size=len(content),
        )

    @classmethod
    def create_test_pdf(cls, page_count: int = 1) -> "TestFile":
        """Create a test PDF file with the specified number of pages."""
        # This is a minimal PDF file with the specified number of pages
        pdf_parts = [
            b"%PDF-1.4\n",
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            f"2 0 obj\n<< /Type /Pages /Kids [{' '.join(f'{i} 0 R' for i in range(3, 3 + page_count))}] /Count {page_count} >>\nendobj\n".encode(
                "utf-8"
            ),
        ]

        # Add pages
        for i in range(page_count):
            pdf_parts.append(
                f"{i + 3} 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] >>\nendobj\n".encode(
                    "utf-8"
                )
            )

        # Add xref and trailer
        xref_offset = sum(len(part) for part in pdf_parts)
        xref = [
            b"xref\n",
            f"0 {3 + page_count}\n".encode("utf-8"),
            b"0000000000 65535 f \n",  # First object is always free
        ]

        # Add xref entries for each object
        offset = 0
        for i in range(
            1, 3 + page_count
        ):  # +3 for catalog, pages, and each page
            xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
            if i < len(pdf_parts) - 1:  # Not the last part
                offset += len(pdf_parts[i - 1])

        pdf_parts.extend(xref)

        # Add trailer
        trailer = [
            b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (3 + page_count),
            b"startxref\n%d\n" % xref_offset,
            b"%%EOF",
        ]
        pdf_parts.extend(trailer)

        content = b"".join(pdf_parts)

        return cls(
            filename=f"test_document_{page_count}_pages.pdf",
            content=content,
            content_type="application/pdf",
            size=len(content),
        )


# Test files with different scenarios
TEST_FILES = {
    "small_image": TestFile.create_test_image(100, 100, "white"),
    "large_image": TestFile.create_test_image(2000, 2000, "blue"),
    "single_page_pdf": TestFile.create_test_pdf(1),
    "multi_page_pdf": TestFile.create_test_pdf(5),
}

# Test cases for file upload
UPLOAD_TEST_CASES = [
    # (test_name, file_type, expected_status, expected_detail)
    ("valid_image", "small_image", 200, None),
    ("large_image", "large_image", 200, None),
    ("valid_pdf", "single_page_pdf", 200, None),
    ("multi_page_pdf", "multi_page_pdf", 200, None),
]

# Test cases for file download
DOWNLOAD_TEST_CASES = [
    # (test_name, file_type, expected_status, expected_detail)
    ("existing_file", "small_image", 200, None),
    ("non_existent_file", "nonexistent", 404, "File not found"),
]

# Test cases for file deletion
DELETE_TEST_CASES = [
    # (test_name, file_type, expected_status, expected_detail)
    ("existing_file", "small_image", 200, "File deleted successfully"),
    ("non_existent_file", "nonexistent", 404, "File not found"),
    ("already_deleted", "small_image", 404, "File not found"),
]


class TestFileOperations:
    """Test file operations including upload, download, list, and delete."""

    @pytest.fixture
    def test_image(self) -> bytes:
        """Generate a test image for upload tests."""
        img = Image.new("RGB", (22, 22), color="black")
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

    @pytest.mark.parametrize(
        "test_name, file_type, expected_status, expected_detail",
        UPLOAD_TEST_CASES,
        ids=[tc[0] for tc in UPLOAD_TEST_CASES],
    )
    def test_upload_file_parameterized(
        self,
        authorized_client: TestClient,
        test_name: str,
        file_type: str,
        expected_status: int,
        expected_detail: Optional[str],
    ) -> None:
        """Test uploading different types of files with various scenarios."""
        if file_type not in TEST_FILES and file_type != "nonexistent":
            pytest.skip(f"Test file type '{file_type}' not defined")

        test_file = TEST_FILES.get(
            file_type,
            {
                "filename": "nonexistent.txt",
                "content": b"",
                "content_type": "text/plain",
                "size": 0,
            },
        )

        response = authorized_client.post(
            "/api/v1/files/upload-image/",
            files={
                "file": (
                    test_file.filename,
                    test_file.content,
                    test_file.content_type,
                )
            },
        )

        assert response.status_code == expected_status

        if expected_status == 200:
            data = response.json()
            assert "id" in data
            assert data["filename"] == test_file.filename
            assert data["content_type"] == test_file.content_type
            assert data["size"] == test_file.size

            # Verify file exists on disk
            file_path = Path(data["filepath"])
            assert file_path.exists()
            assert file_path.stat().st_size == test_file.size
        elif expected_detail:
            assert expected_detail in response.json().get("detail", "")

    @pytest.mark.parametrize(
        "test_name, file_type, expected_status, expected_detail",
        DOWNLOAD_TEST_CASES,
        ids=[tc[0] for tc in DOWNLOAD_TEST_CASES],
    )
    def test_download_file_parameterized(
        self,
        authorized_client: TestClient,
        test_name: str,
        file_type: str,
        expected_status: int,
        expected_detail: Optional[str],
    ) -> None:
        """Test downloading files with various scenarios."""
        if file_type == "nonexistent":
            # Test case for non-existent file
            file_id = "00000000-0000-0000-0000-000000000000"
        else:
            if file_type not in TEST_FILES:
                pytest.skip(f"Test file type '{file_type}' not defined")

            # Upload a test file first
            test_file = TEST_FILES[file_type]
            upload_response = authorized_client.post(
                "/api/v1/files/upload-image/",
                files={
                    "file": (
                        test_file.filename,
                        test_file.content,
                        test_file.content_type,
                    )
                },
            )
            assert upload_response.status_code == 200
            file_id = upload_response.json()["id"]

        # Attempt to download the file
        response = authorized_client.get(f"/api/v1/files/download/{file_id}")

        assert response.status_code == expected_status

        if expected_status == 200:
            assert response.content == test_file.content
            assert "content-disposition" in response.headers
            assert (
                f'filename="{test_file.filename}"'
                in response.headers["content-disposition"]
            )
        elif expected_detail:
            assert expected_detail in response.json().get("detail", "")

    @pytest.mark.parametrize(
        "test_name, file_type, expected_status, expected_detail",
        DELETE_TEST_CASES,
        ids=[tc[0] for tc in DELETE_TEST_CASES],
    )
    def test_delete_file_parameterized(
        self,
        authorized_client: TestClient,
        test_name: str,
        file_type: str,
        expected_status: int,
        expected_detail: Optional[str],
    ) -> None:
        """Test deleting files with various scenarios."""
        file_id = None
        file_path = None

        if file_type == "nonexistent":
            # Test case for non-existent file
            file_id = "00000000-0000-0000-0000-000000000000"
        else:
            if file_type not in TEST_FILES:
                pytest.skip(f"Test file type '{file_type}' not defined")

            # Upload a test file first
            test_file = TEST_FILES[file_type]
            upload_response = authorized_client.post(
                "/api/v1/files/upload-image/",
                files={
                    "file": (
                        test_file.filename,
                        test_file.content,
                        test_file.content_type,
                    )
                },
            )
            assert upload_response.status_code == 200
            file_data = upload_response.json()
            file_id = file_data["id"]
            file_path = Path(file_data["filepath"])

            # For the "already_deleted" test case, delete the file first
            if test_name == "already_deleted":
                del_response = authorized_client.delete(
                    f"/api/v1/files/delete/{file_id}"
                )
                assert del_response.status_code == 200

        # Attempt to delete the file
        response = authorized_client.delete(f"/api/v1/files/delete/{file_id}")

        assert response.status_code == expected_status

        if expected_status == 200:
            assert response.json().get("message") == expected_detail

            # Verify file is marked as deleted in the database
            response = authorized_client.get(f"/api/v1/files/info/{file_id}")
            assert response.status_code == 404

            # Verify file is actually deleted from disk
            if file_path:
                assert not file_path.exists()
        elif expected_detail:
            assert expected_detail in response.json().get("detail", "")

    def test_upload_image(
        self,
        authorized_client: TestClient,
        test_image: bytes,
        db_session: Session,
    ) -> None:
        """Test uploading an image file."""
        # Prepare file for upload
        files = {"file": ("test.png", test_image, "image/png")}

        # Make request
        response = authorized_client.post(
            "/api/v1/files/upload-image/", files=files
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["filename"] == "test.png"
        assert data["content_type"] == "image/png"
        assert data["size"] > 0

        # Verify file exists in database
        file_id = data["id"]
        file_db = (
            db_session.query(FileModel).filter(FileModel.id == file_id).first()
        )
        assert file_db is not None
        assert Path(file_db.filepath).exists()

    def test_upload_pdf(
        self, authorized_client: TestClient, test_pdf: bytes
    ) -> None:
        """Test uploading a PDF file."""
        # Prepare file for upload
        files = {"file": ("test.pdf", test_pdf, "application/pdf")}

        # Make request
        response = authorized_client.post(
            "/api/v1/files/upload-image/", files=files
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["content_type"] == "application/pdf"

    def test_upload_unsupported_file_type(
        self, authorized_client: TestClient
    ) -> None:
        """Test uploading an unsupported file type."""
        files = {"file": ("test.txt", b"test content", "text/plain")}
        response = authorized_client.post(
            "/api/v1/files/upload-image/", files=files
        )

        assert response.status_code == 400
        assert "File type not supported" in response.json()["detail"]

    def test_download_nonexistent_file(
        self, authorized_client: TestClient
    ) -> None:
        """Test downloading a file that doesn't exist."""
        response = authorized_client.get("/api/v1/files/download/999999")
        assert response.status_code == 404

    def test_list_files(
        self, authorized_client: TestClient, test_file: FileModel
    ) -> None:
        """Test listing user's files."""
        response = authorized_client.get("/api/v1/files/list")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert any(f["id"] == test_file.id for f in data)

    def test_get_file_metadata(
        self, authorized_client: TestClient, test_file: FileModel
    ) -> None:
        """Test getting file metadata."""
        response = authorized_client.get(f"/api/v1/files/info/{test_file.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_file.id
        assert data["filename"] == test_file.filename
        assert "filepath" not in data  # Sensitive path not exposed

    def test_convert_image_to_pdf(
        self,
        authorized_client: TestClient,
        test_image: bytes,
        db_session: Session,
    ) -> None:
        """Test converting an image to PDF."""
        # Upload image
        files = {"file": ("test.png", test_image, "image/png")}
        response = authorized_client.post(
            "/api/v1/files/convert-image-to-pdf/", files=files
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "file_id" in data

        # In test environment with eager tasks, the conversion is synchronous
        file_id = data["file_id"]
        pdf_file = (
            db_session.query(FileModel).filter(FileModel.id == file_id).first()
        )

        assert pdf_file is not None
        assert pdf_file.content_type == "application/pdf"
        assert pdf_file.filename.endswith(".pdf")
        assert Path(pdf_file.filepath).exists()

    def test_merge_pdfs(
        self,
        authorized_client: TestClient,
        test_pdf: bytes,
        db_session: Session,
    ) -> None:
        """Test merging multiple PDFs."""
        # Upload first PDF
        file_1 = {"files": ("test1.pdf", test_pdf, "application/pdf")}
        response1 = authorized_client.post(
            "/api/v1/files/upload-image/", files=file_1
        )
        file_1_id = response1.json()["id"]

        # Upload second PDF
        file_2 = {"files": ("test2.pdf", test_pdf, "application/pdf")}
        response2 = authorized_client.post(
            "/api/v1/files/upload-image/", files=file_2
        )
        file_2_id = response2.json()["id"]

        # Merge PDFs
        merge_data = {"file_ids": [file_1_id, file_2_id]}
        response = authorized_client.post(
            "/api/v1/files/merge-pdfs/",  # This endpoint needs to be implemented
            json=merge_data,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "file_id" in data

        # In test environment with eager tasks, the merge is synchronous
        merged_file_id = data["file_id"]
        merged_file = (
            db_session.query(FileModel)
            .filter(FileModel.id == merged_file_id)
            .first()
        )

        assert merged_file is not None
        assert merged_file.content_type == "application/pdf"
        assert "merged_" in merged_file.filename
        assert Path(merged_file.filepath).exists()

        # Step 5: Download the converted PDF
        response = authorized_client.get(
            f"/api/v1/files/{merged_file_id}/download"
        )
        assert response.status_code == 200
        expected_disposition = 'attachment; filename="test_image.pdf"'
        assert response.headers["content-disposition"] == expected_disposition
        assert response.content.startswith(b"%PDF-")

        # Step 6: Clean up the created file on disk
        Path(merged_file.filepath).unlink()
        Path(file_1.filepath).unlink()
        Path(file_2.filepath).unlink()
