from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.file import File, FileCreate
from app.schemas.pdf import MergePdfsRequest, MergeTaskResponse
from app.schemas.tasks import TaskResponse


def test_file_schema():
    """
    Tests the File schema to ensure it correctly validates data.
    """
    now = datetime.now()
    file_data = {
        "id": 1,
        "filename": "test.pdf",
        "created_at": now,
        "url": "http://example.com/files/1",  # Add a valid URL
    }
    file_instance = File(**file_data)

    assert file_instance.id == 1
    assert file_instance.filename == "test.pdf"
    assert file_instance.created_at == now
    assert str(file_instance.url) == "http://example.com/files/1"


def test_file_create_schema():
    """
    Tests the FileCreate schema.
    """
    file_data = {"filename": "new_file.txt", "filepath": "/tmp/new_file.txt"}
    file_create_instance = FileCreate(**file_data)
    assert file_create_instance.filename == "new_file.txt"
    assert file_create_instance.filepath == "/tmp/new_file.txt"


def test_file_schema_invalid_data():
    """
    Tests that the File schema raises a validation error for invalid data.
    """
    with pytest.raises(ValidationError):
        File(id="not_an_integer", filename=123)


def test_task_response_schema():
    """
    Tests the TaskResponse schema to ensure it correctly validates data.
    """
    # Test with valid data
    task_data = {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "file_id": 123,
    }
    task_response = TaskResponse(**task_data)

    assert task_response.task_id == task_data["task_id"]
    assert task_response.file_id == task_data["file_id"]

    # Test with invalid task_id (not a string)
    with pytest.raises(ValidationError):
        TaskResponse(task_id=123, file_id=123)

    # Test with invalid file_id (not an integer)
    with pytest.raises(ValidationError):
        TaskResponse(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            file_id="not_an_integer",
        )


def test_merge_pdfs_request_schema():
    """
    Tests the MergePdfsRequest schema to ensure it correctly validates data.
    """
    # Test with valid data
    request_data = {"file_ids": [1, 2, 3], "output_filename": "merged.pdf"}
    merge_request = MergePdfsRequest(**request_data)

    assert merge_request.file_ids == request_data["file_ids"]
    assert merge_request.output_filename == request_data["output_filename"]

    # Test with empty file_ids list (this is actually allowed by the model)
    request_data_empty = {"file_ids": [], "output_filename": "empty.pdf"}
    merge_request_empty = MergePdfsRequest(**request_data_empty)
    assert merge_request_empty.file_ids == []

    # Test with missing output_filename
    with pytest.raises(ValidationError):
        MergePdfsRequest(file_ids=[1, 2, 3])

    # Test with invalid file_ids (not a list of integers)
    with pytest.raises(ValidationError):
        MergePdfsRequest(
            file_ids=[1, "not_an_integer", 3], output_filename="invalid.pdf"
        )


def test_merge_task_response_schema():
    """
    Tests the MergeTaskResponse schema to ensure it correctly validates data.
    """
    # Test with valid data
    response_data = {"task_id": "550e8400-e29b-41d4-a716-446655440000"}
    merge_response = MergeTaskResponse(**response_data)

    assert merge_response.task_id == response_data["task_id"]

    # Test with missing required field
    with pytest.raises(ValidationError):
        MergeTaskResponse()
