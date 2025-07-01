from datetime import datetime

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
        File(id="one", filename="test.pdf", created_at=datetime.now())
