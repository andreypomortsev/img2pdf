import io
from pathlib import Path

from PIL import Image

from app.models.file import File as FileModel


def create_test_image() -> bytes:
    """
    Generates a 1x1 black PNG image for testing.
    """
    img = Image.new("RGB", (1, 1), color="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


PNG_BLACK_DOT = create_test_image()


def test_upload_image(client, db_session, tmp_path):
    """
    Test image upload, conversion task, and file download using filesystem.
    """
    # Step 1: Upload the image
    filename = "test_image.png"
    # Wrap the image bytes in a file-like object to ensure it's handled correctly.
    image_file = io.BytesIO(PNG_BLACK_DOT)
    response = client.post(
        "/api/v1/files/upload-image/",
        files={"file": (filename, image_file, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert "file_id" in data

    task_id = data["task_id"]

    # Step 3: Check task status (should complete eagerly in test mode)
    response = client.get(f"/api/v1/files/tasks/{task_id}")
    assert response.status_code == 200
    task_data = response.json()
    assert task_data["task_status"] == "SUCCESS"
    pdf_file_id = task_data["task_result"]
    assert isinstance(pdf_file_id, int)

    # Step 4: Verify the PDF file exists in the database and on disk
    pdf_file_db = (
        db_session.query(FileModel).filter(FileModel.id == pdf_file_id).first()
    )
    assert pdf_file_db is not None
    assert Path(pdf_file_db.filepath).exists()
    assert pdf_file_db.filename == "test_image_1.pdf"

    # Step 5: Download the converted PDF
    response = client.get(f"/api/v1/files/{pdf_file_id}/download")
    assert response.status_code == 200
    expected_disposition = 'attachment; filename="test_image_1.pdf"'
    assert response.headers["content-disposition"] == expected_disposition
    assert response.content.startswith(b"%PDF-")

    # Step 6: Clean up the created file on disk
    Path(pdf_file_db.filepath).unlink()
