from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@patch("app.api.v1.endpoints.pdfs.file_service.create_merge_task")
def test_merge_pdfs_happy_path(mock_create_merge_task, client):
    """
    Tests the happy path for the /merge/ endpoint with a valid payload.
    """
    mock_task = MagicMock()
    mock_task.id = "test_merge_task_id"
    mock_create_merge_task.return_value = mock_task

    payload = {"file_ids": [1, 2], "output_filename": "merged.pdf"}
    response = client.post("/api/v1/pdfs/merge/", json=payload)

    assert response.status_code == 200, response.json()
    assert response.json() == {"task_id": "test_merge_task_id"}
    mock_create_merge_task.assert_called_once_with(
        file_ids=[1, 2], output_filename="merged.pdf"
    )


def test_merge_pdfs_invalid_payload(client):
    """
    Tests that the /merge/ endpoint returns a 422 error for an invalid payload.
    """
    payload = {"file_ids": [1, 2]}  # Missing output_filename
    response = client.post("/api/v1/pdfs/merge/", json=payload)

    assert response.status_code == 422
