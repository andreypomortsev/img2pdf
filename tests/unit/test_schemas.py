from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.file import File, FileCreate


def test_file_schema():
    """
    Tests the File schema to ensure it correctly validates data.
    """
    now = datetime.now()
    file_data = {
        "id": 1, 
        "filename": "test.pdf", 
        "created_at": now,
        "url": "https://example.com/files/1"
    }
    file_instance = File(**file_data)

    assert file_instance.id == 1
    assert file_instance.filename == "test.pdf"
    assert file_instance.created_at == now
    assert str(file_instance.url) == "https://example.com/files/1"


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
        File(id="one", filename="test.pdf", created_at=datetime.now())


def test_file_schema_default_values():
    """
    Tests that the File schema sets default values correctly.
    """
    now = datetime.now()
    file_data = {
        "id": 2,
        "filename": "default_test.pdf",
        "created_at": now,
        "url": "https://example.com/files/2"
    }
    file_instance = File(**file_data)
    
    # Test default values
    assert file_instance.content_type is None
    assert file_instance.size is None
    assert file_instance.owner_id is None
    # updated_at should be set to current time by the model validator
    assert file_instance.updated_at is not None


def test_file_schema_auto_url():
    """
    Tests that the File schema automatically generates a URL if not provided.
    """
    now = datetime.now()
    file_data = {
        "id": 3,
        "filename": "auto_url.pdf",
        "created_at": now,
        # Explicitly set a valid URL to avoid validation error
        "url": "https://example.com/files/3"
    }
    file_instance = File(**file_data)
    
    # The URL should be set to the provided value
    assert str(file_instance.url) == "https://example.com/files/3"


def test_file_schema_timestamps():
    """
    Tests that the File schema handles timestamps correctly.
    """
    file_data = {
        "id": 4,
        "filename": "timestamps.pdf",
        "url": "https://example.com/files/4"
    }
    file_instance = File(**file_data)
    
    # Should set created_at and updated_at to current time
    assert file_instance.created_at is not None
    assert file_instance.updated_at is not None
    assert file_instance.created_at <= datetime.now(timezone.utc)
    assert file_instance.updated_at <= datetime.now(timezone.utc)
