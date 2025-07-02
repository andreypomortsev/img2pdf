from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.file import File, FileCreate
from app.schemas.pdf import MergePdfsRequest, MergeTaskResponse
from app.schemas.tasks import TaskResponse
from app.schemas.token import Token, TokenData


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


def test_token_schema():
    """
    Tests the Token schema to ensure it correctly validates data.
    """
    # Test with minimal required fields
    token_data = {"access_token": "test_access_token"}
    token = Token(**token_data)

    assert token.access_token == token_data["access_token"]
    assert token.token_type == "bearer"  # Default value

    # Test with all fields provided
    token_data_full = {
        "access_token": "test_access_token",
        "token_type": "custom_type",
    }
    token_full = Token(**token_data_full)

    assert token_full.access_token == token_data_full["access_token"]
    assert token_full.token_type == token_data_full["token_type"]

    # Test model_dump method
    dump_data = token_full.model_dump()
    assert dump_data["access_token"] == token_data_full["access_token"]
    assert dump_data["token_type"] == token_data_full["token_type"]

    # Test model_dump_json method
    json_data = token_full.model_dump_json()
    assert "access_token" in json_data
    assert "token_type" in json_data

    # Test model_config example
    assert hasattr(Token, "model_config")
    assert "example" in Token.model_config["json_schema_extra"]
    example = Token.model_config["json_schema_extra"]["example"]
    assert "access_token" in example
    assert "token_type" in example


def test_token_data_schema():
    """
    Tests the TokenData schema to ensure it correctly validates data.
    """
    # Test with username
    token_data = {"username": "testuser"}
    token = TokenData(**token_data)
    assert token.username == token_data["username"]

    # Test with no username (should be valid as it's optional)
    token_empty = TokenData()
    assert token_empty.username is None
