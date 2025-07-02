"""Tests for the file schemas."""

import unittest
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.file import (File, FileBase, FileCreate, FileInDB,
                              FileInDBBase, FileUpdate)


def test_file_base_validation():
    """Test validation of FileBase schema."""
    # Test valid data
    file_data = {
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "size": 1024,
    }
    file = FileBase(**file_data)
    assert file.filename == "test.pdf"
    assert file.content_type == "application/pdf"
    assert file.size == 1024

    # Test with only required fields
    file = FileBase(filename="test.pdf")
    assert file.filename == "test.pdf"
    assert file.content_type is None
    assert file.size is None


def test_file_create_validation():
    """Test validation of FileCreate schema."""
    # Test valid data
    file_data = {
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "size": 1024,
        "filepath": "/path/to/file.pdf",
        "owner_id": 1,
    }
    file = FileCreate(**file_data)
    assert file.filename == "test.pdf"
    assert file.content_type == "application/pdf"
    assert file.size == 1024
    assert file.filepath == "/path/to/file.pdf"
    assert file.owner_id == 1

    # Test with only required fields
    file = FileCreate(filename="test.pdf", filepath="/path/to/file.pdf")
    assert file.filename == "test.pdf"
    assert file.filepath == "/path/to/file.pdf"
    assert file.owner_id is None

    # Test missing required fields
    with pytest.raises(ValidationError):
        FileCreate(filename="test.pdf")  # Missing filepath

    with pytest.raises(ValidationError):
        FileCreate(filepath="/path/to/file.pdf")  # Missing filename


def test_file_update_validation():
    """Test validation of FileUpdate schema."""
    # Test with all fields
    file_data = {
        "filename": "updated.pdf",
        "content_type": "application/pdf",
        "size": 2048,
    }
    file = FileUpdate(**file_data)
    assert file.filename == "updated.pdf"
    assert file.content_type == "application/pdf"
    assert file.size == 2048

    # Test with partial updates
    file = FileUpdate(filename="updated.pdf")
    assert file.filename == "updated.pdf"
    assert file.content_type is None
    assert file.size is None

    file = FileUpdate(content_type="image/png")
    assert file.filename is None
    assert file.content_type == "image/png"
    assert file.size is None


def test_file_in_db_base_validation():
    """Test validation of FileInDBBase schema."""
    now = datetime.now(timezone.utc)

    # Test with all fields
    file_data = {
        "id": 1,
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "size": 1024,
        "owner_id": 1,
        "created_at": now,
        "updated_at": now,
    }
    file = FileInDBBase(**file_data)
    assert file.id == 1
    assert file.filename == "test.pdf"
    assert file.owner_id == 1
    assert file.created_at == now
    assert file.updated_at == now

    # Test with timestamps set by model validator
    file_data = {
        "id": 2,
        "filename": "test2.pdf",
    }
    file = FileInDBBase(**file_data)
    assert file.id == 2
    assert file.filename == "test2.pdf"
    assert file.created_at is not None
    assert file.updated_at is not None
    assert isinstance(file.created_at, datetime)
    assert isinstance(file.updated_at, datetime)


def test_file_in_db_base_serialization():
    """Test serialization of FileInDBBase schema."""
    now = datetime.now(timezone.utc)
    file_data = {
        "id": 1,
        "filename": "test.pdf",
        "created_at": now,
        "updated_at": now,
    }

    # Test model_dump
    file = FileInDBBase(**file_data)
    dumped = file.model_dump()

    # Handle both 'Z' and '+00:00' timezone formats
    created_at = dumped["created_at"]
    updated_at = dumped["updated_at"]
    assert (
        created_at == now.isoformat()
        or created_at == now.isoformat().replace("+00:00", "Z")
    )
    assert (
        updated_at == now.isoformat()
        or updated_at == now.isoformat().replace("+00:00", "Z")
    )

    # Test model_dump_json
    json_data = file.model_dump_json()
    assert '"created_at":"' in json_data
    assert '"updated_at":"' in json_data
    assert json_data.endswith("}")


def test_file_in_db_validation():
    """Test validation of FileInDB schema."""
    now = datetime.now(timezone.utc)

    # Test with all fields
    file_data = {
        "id": 1,
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "size": 1024,
        "owner_id": 1,
        "created_at": now,
        "updated_at": now,
        "filepath": "/path/to/file.pdf",
    }
    file = FileInDB(**file_data)
    assert file.id == 1
    assert file.filename == "test.pdf"
    assert file.filepath == "/path/to/file.pdf"

    # Test missing required field
    with pytest.raises(ValidationError):
        FileInDB(
            id=1,
            filename="test.pdf",
            created_at=now,
            updated_at=now,
            # Missing filepath
        )


def test_file_validation():
    """Test validation of File schema."""
    now = datetime.now(timezone.utc)

    # Test with all fields
    file_data = {
        "id": 1,
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "size": 1024,
        "owner_id": 1,
        "created_at": now,
        "updated_at": now,
        "url": "https://example.com/files/1",
    }
    file = File(**file_data)
    assert file.id == 1
    assert file.filename == "test.pdf"
    assert str(file.url) == "https://example.com/files/1"

    # Test with a full URL in the data
    file_data = {
        "id": 1,
        "filename": "test.pdf",
        "created_at": now,
        "url": "https://example.com/files/1",
    }
    file = File(**file_data)
    assert file.url is not None
    assert str(file.url) == "https://example.com/files/1"


def test_file_config_example():
    """Test that the example in the config validates correctly."""
    example = FileInDBBase.model_config["json_schema_extra"]["example"]
    file = FileInDBBase(**example)
    assert file.id == 1
    assert file.filename == "example.pdf"
    assert file.content_type == "application/pdf"
    assert file.size == 1024
    assert file.owner_id == 1
    assert isinstance(file.created_at, datetime)
    assert isinstance(file.updated_at, datetime)


def test_file_model_dump_json():
    """Test the custom model_dump_json method."""
    now = datetime.now(timezone.utc)
    file = FileInDBBase(
        id=1, filename="test.pdf", created_at=now, updated_at=now
    )
    json_data = file.model_dump_json()
    assert '"id":1' in json_data
    assert '"filename":"test.pdf"' in json_data
    assert '"created_at":"' in json_data
    assert '"updated_at":"' in json_data


def test_file_model_dump_exclude_fields():
    """Test model_dump with excluded fields."""
    # Test with fields excluded from the dump
    file = FileInDBBase(
        id=1,
        filename="test.pdf",
        created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2023, 1, 2, tzinfo=timezone.utc),
    )
    # Exclude updated_at from the dump
    data = file.model_dump(exclude={"updated_at"})
    assert "id" in data
    assert "filename" in data
    assert "created_at" in data
    assert "updated_at" not in data  # This field was excluded
    assert data["created_at"] == "2023-01-01T00:00:00+00:00"


def test_file_model_dump():
    """Test the custom model_dump method."""
    # Test with a field explicitly set to None
    file = FileInDBBase(
        id=1,
        filename="test.pdf",
        created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        updated_at=None,  # Explicitly set to None
    )
    data = file.model_dump()
    assert data["created_at"] == "2023-01-01T00:00:00+00:00"
    assert "updated_at" in data  # Should be in data but not None
    assert data["updated_at"] is not None  # Should be set by set_timestamps
    assert isinstance(
        datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
        datetime,
    )

    # Test with both timestamps explicitly set
    created = datetime(2023, 1, 1, tzinfo=timezone.utc)
    updated = datetime(2023, 1, 2, tzinfo=timezone.utc)
    file = FileInDBBase(
        id=1, filename="test.pdf", created_at=created, updated_at=updated
    )
    data = file.model_dump()
    assert data["created_at"] == "2023-01-01T00:00:00+00:00"
    assert data["updated_at"] == "2023-01-02T00:00:00+00:00"

    # Test with created_at only - updated_at should be set automatically
    created = datetime(2023, 1, 1, tzinfo=timezone.utc)
    file = FileInDBBase(
        id=1,
        filename="test.pdf",
        created_at=created,
    )
    data = file.model_dump()
    assert data["created_at"] == "2023-01-01T00:00:00+00:00"
    assert "updated_at" in data  # Should be set by set_timestamps
    assert isinstance(
        datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
        datetime,
    )

    # Test with None values - should be handled by set_timestamps
    file = FileInDBBase(
        id=1,
        filename="test.pdf",
        created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        updated_at=None,
    )
    data = file.model_dump()
    assert data["created_at"] == "2023-01-01T00:00:00+00:00"
    assert "updated_at" in data  # Should be set by set_timestamps

    # Test with no timestamps
    data = {"id": 1, "filename": "test.pdf"}
    file = FileInDBBase(**data)
    assert file.created_at is not None
    assert file.updated_at is not None

    # Test with existing timestamps
    now = datetime.now(timezone.utc)
    data = {
        "id": 1,
        "filename": "test.pdf",
        "created_at": now,
        "updated_at": now,
    }
    file = FileInDBBase(**data)
    assert file.created_at == now
    assert file.updated_at == now


def test_file_set_url():
    """Test the set_url validator in File schema."""
    # Test with non-dict input
    result = File.set_url("not a dict")
    assert result == "not a dict"

    # Test with dict input but no id
    data = {"filename": "test.pdf"}
    result = File.set_url(data)
    assert result == data  # Should return unchanged

    # Test with dict input with id but no url
    base_url = "http://localhost:8000"
    with unittest.mock.patch("app.schemas.file.settings") as mock_settings:
        # Remove SERVER_HOST if it exists
        if hasattr(mock_settings, "SERVER_HOST"):
            delattr(mock_settings, "SERVER_HOST")

        data = {"id": 1, "filename": "test.pdf"}
        result = File.set_url(data)
        assert "url" in result
        assert str(result["url"]) == f"{base_url}/files/1"

    # Test with existing URL - should use the provided URL
    file = File(id=1, filename="test.pdf", url="https://example.com/custom/1")
    assert str(file.url) == "https://example.com/custom/1"

    # Test with default URL when SERVER_HOST is not set
    with unittest.mock.patch("app.schemas.file.settings") as mock_settings:
        # Remove SERVER_HOST if it exists
        if hasattr(mock_settings, "SERVER_HOST"):
            delattr(mock_settings, "SERVER_HOST")

        file = File(id=1, filename="test.pdf")
        assert file.url is not None
        assert str(file.url) == f"{base_url}/files/1"

    # Test with custom SERVER_HOST from config
    custom_host = "https://api.example.com"
    with unittest.mock.patch("app.schemas.file.settings") as mock_settings:
        mock_settings.SERVER_HOST = custom_host
        file = File(id=1, filename="test.pdf")
        assert file.url is not None
        assert str(file.url) == f"{custom_host}/files/1"


def test_file_in_db_validation_without_filepath():
    """Test FileInDB validation without required filepath."""
    with pytest.raises(ValueError):
        FileInDB(id=1, filename="test.pdf")


def test_file_set_timestamps():
    """Test the set_timestamps validator."""
    # Test with non-dict input
    result = FileInDBBase.set_timestamps("not a dict")
    assert result == "not a dict"

    # Test with dict input, missing timestamps
    now = datetime.now(timezone.utc)
    data = {"filename": "test.pdf"}
    result = FileInDBBase.set_timestamps(data)
    assert "created_at" in result
    assert "updated_at" in result
    assert isinstance(result["created_at"], datetime)
    assert isinstance(result["updated_at"], datetime)
    assert result["created_at"] >= now
    assert result["updated_at"] >= now

    # Test with dict input, missing only updated_at
    created = datetime(2023, 1, 1, tzinfo=timezone.utc)
    data = {"filename": "test.pdf", "created_at": created}
    result = FileInDBBase.set_timestamps(data)
    assert result["created_at"] == created
    assert "updated_at" in result
    assert isinstance(result["updated_at"], datetime)
    assert result["updated_at"] >= now
    # Test with no timestamps
    data = {"id": 1, "filename": "test.pdf"}
    file = FileInDBBase(**data)
    assert file.created_at is not None
    assert file.updated_at is not None

    # Test with existing timestamps
    now = datetime.now(timezone.utc)
    data = {
        "id": 1,
        "filename": "test.pdf",
        "created_at": now,
        "updated_at": now,
    }
    file = FileInDBBase(**data)
    assert file.created_at == now
    assert file.updated_at == now
