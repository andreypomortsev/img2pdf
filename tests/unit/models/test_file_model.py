"""Tests for the File model."""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.file import File


def test_file_creation(db_session, test_user):
    """Test creating a new file."""
    file = File(
        filename="test.txt",
        filepath="/uploads/test.txt",
        size=1024,
        content_type="text/plain",
        owner_id=test_user.id,
    )
    db_session.add(file)
    db_session.commit()
    db_session.refresh(file)

    assert file.id is not None
    assert file.filename == "test.txt"
    assert file.filepath == "/uploads/test.txt"
    assert file.size == 1024
    assert file.content_type == "text/plain"
    assert file.owner_id == test_user.id
    assert isinstance(file.created_at, datetime)
    assert isinstance(file.updated_at, datetime)
    assert file.owner == test_user


def test_file_required_fields(db_session, test_user):
    """Test that required fields cannot be null."""
    # Test missing filename
    file1 = File(
        filepath="/uploads/test.txt",
        size=1024,
        content_type="text/plain",
        owner_id=test_user.id,
    )
    db_session.add(file1)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Test missing filepath
    file2 = File(
        filename="test.txt",
        size=1024,
        content_type="text/plain",
        owner_id=test_user.id,
    )
    db_session.add(file2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Test missing owner_id
    file3 = File(
        filename="test.txt",
        filepath="/uploads/test.txt",
        size=1024,
        content_type="text/plain",
    )
    db_session.add(file3)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_file_relationships(db_session, test_user):
    """Test relationships with other models."""
    # Create a file
    file = File(
        filename="test.txt",
        filepath="/uploads/test.txt",
        size=1024,
        content_type="text/plain",
        owner_id=test_user.id,
    )
    db_session.add(file)
    db_session.commit()
    db_session.refresh(file)

    # Test relationship with owner
    assert file.owner == test_user
    assert file in test_user.files


def test_file_update_timestamps(db_session, test_user):
    """Test that timestamps are updated correctly."""
    # Create file
    file = File(
        filename="test.txt",
        filepath="/uploads/test.txt",
        size=1024,
        content_type="text/plain",
        owner_id=test_user.id,
    )
    db_session.add(file)
    db_session.commit()
    db_session.refresh(file)

    created_at = file.created_at
    updated_at = file.updated_at

    # Ensure we have different timestamps by adding a small delay
    import time

    time.sleep(1.1)  # Sleep for more than a second to ensure timestamp changes

    # Update file
    file.filename = "updated.txt"
    db_session.commit()
    db_session.refresh(file)

    # Created at should not change
    assert (
        file.created_at == created_at
    ), "created_at should not change after update"

    # Convert datetimes to timestamps (seconds since epoch) for comparison
    updated_at_ts = updated_at.timestamp()
    new_updated_at_ts = file.updated_at.timestamp()

    # Updated at should be newer (with at least 1 second difference due to our sleep)
    assert (
        new_updated_at_ts > updated_at_ts
    ), f"updated_at should increase after update (was {updated_at}, now {file.updated_at})"


def test_file_soft_delete(db_session, test_user):
    """Test soft delete functionality."""
    file = File(
        filename="test.txt",
        filepath="/uploads/test.txt",
        size=1024,
        content_type="text/plain",
        owner_id=test_user.id,
    )
    db_session.add(file)
    db_session.commit()
    db_session.refresh(file)

    # Verify initial state
    assert file.is_deleted is False
    assert file.deleted_at is None

    # Soft delete using the delete method
    file.delete()
    db_session.commit()
    db_session.refresh(file)

    # Verify soft delete was successful
    assert file.is_deleted is True
    assert file.deleted_at is not None
    assert isinstance(file.deleted_at, datetime)
