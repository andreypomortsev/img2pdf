import io
from pathlib import Path

from PIL import Image

from app.models.file import File as FileModel

# Polling mechanism removed - Celery tasks now run in eager mode during tests


def test_merge_pdfs(client, db_session, celery_db_session, tmp_path):
    """
    Test uploading multiple images, converting them, merging the resulting
    PDFs, and downloading the final merged PDF using filesystem.
    """
    pdf_file_ids = []
    created_files = []

    # Step 1: Generate a valid test image and upload it twice
    image = Image.new("RGB", (100, 100), color="red")
    image_bytes_io = io.BytesIO()
    image.save(image_bytes_io, format="PNG")
    image_content = image_bytes_io.getvalue()

    for i in range(1, 3):
        image_path = tmp_path / f"test_image_{i}.png"
        image_path.write_bytes(image_content)

        with open(image_path, "rb") as f:
            response = client.post(
                "/api/v1/files/upload-image/",
                files={"file": (image_path.name, f, "image/png")},
            )
        assert response.status_code == 200
        upload_data = response.json()
        task_id = upload_data["task_id"]

        # Task should complete immediately in eager mode
        response = client.get(f"/api/v1/files/tasks/{task_id}")
        assert response.status_code == 200
        task_data = response.json()
        assert task_data["task_status"] == "SUCCESS"
        converted_pdf_id = task_data["task_result"]
        pdf_file_ids.append(converted_pdf_id)

    # Step 2: Merge the two PDFs
    assert len(pdf_file_ids) == 2
    merge_request_data = {
        "file_ids": pdf_file_ids,
        "output_filename": "merged_document.pdf",
    }
    response = client.post("/api/v1/pdfs/merge/", json=merge_request_data)
    assert response.status_code == 200
    merge_task_data = response.json()
    merge_task_id = merge_task_data["task_id"]

    # Step 3: Check merge task status (should complete immediately in eager mode)
    response = client.get(f"/api/v1/files/tasks/{merge_task_id}")
    assert response.status_code == 200
    task_data = response.json()
    assert task_data["task_status"] == "SUCCESS"
    merged_pdf_id = task_data["task_result"]

    # Step 4: Verify the merged PDF exists and download it
    merged_file_db = (
        db_session.query(FileModel).filter(FileModel.id == merged_pdf_id).first()
    )
    assert merged_file_db is not None
    assert Path(merged_file_db.filepath).exists()
    created_files.append(Path(merged_file_db.filepath))

    response = client.get(f"/api/v1/files/{merged_pdf_id}/download")
    assert response.status_code == 200
    expected_disposition = 'attachment; filename="merged_document.pdf"'
    assert response.headers["content-disposition"] == expected_disposition
    assert response.content.startswith(b"%PDF-")

    # Step 5: Clean up all created files
    for file_id in pdf_file_ids:
        file_db = db_session.query(FileModel).filter(FileModel.id == file_id).first()
        if file_db and Path(file_db.filepath).exists():
            created_files.append(Path(file_db.filepath))

    for f in created_files:
        if f.exists():
            f.unlink()
