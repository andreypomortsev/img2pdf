from unittest.mock import ANY, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.file import File as FileModel
from app.worker import celery_app


@pytest.fixture
def client():
    return TestClient(app)


@patch("app.api.v1.endpoints.files.file_service.save_file")
@patch("app.api.v1.endpoints.files.convert_image_to_pdf.delay")
def test_upload_image(mock_convert_task, mock_save_file, client, tmp_path):
    """
    Tests the happy path for the /upload-image endpoint.
    """
    mock_file = MagicMock()
    mock_file.id = 1
    mock_save_file.return_value = mock_file

    mock_task = MagicMock()
    mock_task.id = "test_task_id"
    mock_convert_task.return_value = mock_task

    test_file = tmp_path / "test.png"
    with open(test_file, "wb") as f:
        f.write(b"fake image data")

    with open(test_file, "rb") as f:
        response = client.post(
            "/api/v1/files/upload-image/", files={"file": ("test.png", f, "image/png")}
        )

    assert response.status_code == 200
    assert response.json() == {"task_id": "test_task_id", "file_id": 1}

    mock_save_file.assert_called_once()
    mock_convert_task.assert_called_once_with(1)


@patch("app.api.v1.endpoints.files.file_service.save_file")
@patch("app.api.v1.endpoints.files.convert_image_to_pdf.delay")
def test_upload_image_invalid_file_type(
    mock_convert_task, mock_save_file, client, tmp_path
):
    """
    Tests that uploading a non-image file returns a 400 error.
    """
    mock_convert_task.return_value.id = "mock_task_id"
    test_file = tmp_path / "test.txt"
    with open(test_file, "wb") as f:
        f.write(b"this is not an image")

    with open(test_file, "rb") as f:
        response = client.post(
            "/api/v1/files/upload-image/",
            files={"file": ("test.txt", f, "text/plain")},
        )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

    mock_save_file.assert_not_called()
    mock_convert_task.assert_not_called()


@patch("app.api.v1.endpoints.files.AsyncResult")
def test_get_task_status_success(mock_async_result, client):
    """
    Tests the happy path for the /tasks/{task_id} endpoint when the task is successful.
    """
    mock_result = MagicMock()
    mock_result.status = "SUCCESS"
    mock_result.result = 123  # The task returns the file_id
    mock_async_result.return_value = mock_result

    response = client.get("/api/v1/files/tasks/test_task_id")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "test_task_id",
        "task_status": "SUCCESS",
        "task_result": 123,
    }
    mock_async_result.assert_called_once_with("test_task_id", app=celery_app)


@patch("app.api.v1.endpoints.files.AsyncResult")
def test_get_task_status_pending(mock_async_result, client):
    """
    Tests the /tasks/{task_id} endpoint when the task is still pending.
    """
    mock_result = MagicMock()
    mock_result.status = "PENDING"
    mock_result.result = None
    mock_async_result.return_value = mock_result

    response = client.get("/api/v1/files/tasks/test_task_id")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "test_task_id",
        "task_status": "PENDING",
        "task_result": None,
    }
    mock_async_result.assert_called_once_with("test_task_id", app=celery_app)


@patch("app.api.v1.endpoints.files.AsyncResult")
def test_get_task_status_failure(mock_async_result, client):
    """
    Tests the /tasks/{task_id} endpoint when the task has failed.
    """
    mock_result = MagicMock()
    mock_result.status = "FAILURE"
    mock_result.result = "Something went wrong"
    mock_async_result.return_value = mock_result

    response = client.get("/api/v1/files/tasks/test_task_id")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "test_task_id",
        "task_status": "FAILURE",
        "task_result": "Something went wrong",
    }
    mock_async_result.assert_called_once_with("test_task_id", app=celery_app)


@patch("app.api.v1.endpoints.files.file_service.get_file_by_id")
def test_download_file_happy_path(mock_get_file_by_id, client, tmp_path):
    """
    Tests the happy path for the /download/{file_id} endpoint.
    """
    # Create a dummy file to be "downloaded"
    file_path = tmp_path / "test.pdf"
    file_path.write_text("dummy pdf content")

    mock_file = FileModel(id=1, filename="test.pdf", filepath=str(file_path))
    mock_get_file_by_id.return_value = mock_file

    response = client.get("/api/v1/files/download/1")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="test.pdf"'
    assert response.content == b"dummy pdf content"
    mock_get_file_by_id.assert_called_once_with(db=ANY, file_id=1)


@patch("app.api.v1.endpoints.files.file_service.get_file_by_id")
def test_download_file_not_found(mock_get_file_by_id, client):
    """
    Tests that the /download/{file_id} endpoint returns a 404 if the file is not found.
    """
    mock_get_file_by_id.return_value = None

    response = client.get("/api/v1/files/download/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "File not found"}

    mock_get_file_by_id.assert_called_once_with(db=ANY, file_id=999)
