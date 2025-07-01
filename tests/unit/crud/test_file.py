"""Tests for the CRUD operations on File model."""

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from app.crud.crud_file import CRUDFile
from app.models.file import File as FileModel
from app.schemas.file import FileCreate, FileUpdate


class TestCRUDFile:
    """Test cases for CRUDFile class."""

    @pytest.fixture
    def test_file(self) -> FileModel:
        """Create a test file instance."""
        file = FileModel(
            id=1,
            filename="test.pdf",
            content_type="application/pdf",
            size=1024,
            filepath="/uploads/test.pdf",
            owner_id=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return file

    @pytest.fixture
    def file_create_data(self) -> Dict[str, Any]:
        """Create test file creation data."""
        return {
            "filename": "test.pdf",
            "content_type": "application/pdf",
            "size": 1024,
            "filepath": "/uploads/test.pdf",
            "owner_id": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    @pytest.fixture
    def file_update_data(self) -> Dict[str, Any]:
        """Create test file update data."""
        return {
            "filename": "updated.pdf",
            "content_type": "application/pdf",
            "size": 2048,
        }

    @pytest.fixture
    def crud_file(self) -> CRUDFile:
        """Create a CRUDFile instance for testing."""
        return CRUDFile(FileModel)

    def test_get_by_id(
        self, mock_db: MagicMock, crud_file: CRUDFile, test_file: FileModel
    ):
        """Test getting a file by ID."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = (
            test_file
        )

        # Act
        result = crud_file.get_by_id(mock_db, id=1)

        # Assert
        assert result == test_file
        mock_db.query.assert_called_once_with(FileModel)
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_by_id_not_found(
        self, mock_db: MagicMock, crud_file: CRUDFile
    ):
        """Test getting a non-existent file by ID returns None."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = (
            None
        )

        # Act
        result = crud_file.get_by_id(mock_db, id=999)

        # Assert
        assert result is None

    def test_get_multi_by_owner(
        self, mock_db: MagicMock, crud_file: CRUDFile, test_file: FileModel
    ):
        """Test getting multiple files by owner ID."""
        # Arrange
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [
            test_file
        ]

        # Act
        result = crud_file.get_multi_by_owner(
            mock_db, owner_id=1, skip=0, limit=10
        )

        # Assert
        assert len(result) == 1
        assert result[0] == test_file
        mock_db.query.assert_called_once_with(FileModel)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.offset.assert_called_once_with(
            0
        )
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.assert_called_once_with(
            10
        )

    def test_create(
        self,
        mock_db: MagicMock,
        crud_file: CRUDFile,
        file_create_data: dict,
        test_file: FileModel,
    ):
        """Test creating a new file."""
        # Arrange
        obj_in = FileCreate(**file_create_data)

        # Track the instance that was added to the session
        added_instance = None

        def add_side_effect(instance, **kwargs):
            nonlocal added_instance
            added_instance = instance

        mock_db.add.side_effect = add_side_effect

        # Act
        result = crud_file.create(mock_db, obj_in=obj_in)

        # Assert
        # Check that the result is a FileModel instance
        assert isinstance(result, FileModel)

        # Verify the base CRUD methods were called
        assert mock_db.add.called
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # Verify the instance passed to add() has the expected attributes
        assert added_instance is not None
        assert added_instance.filename == file_create_data["filename"]
        assert added_instance.filepath == file_create_data["filepath"]
        assert added_instance.content_type == file_create_data["content_type"]
        assert added_instance.size == file_create_data["size"]
        assert added_instance.owner_id == file_create_data["owner_id"]

        # Verify the returned result has the expected attributes
        assert result.filename == file_create_data["filename"]
        assert result.filepath == file_create_data["filepath"]
        assert result.content_type == file_create_data["content_type"]
        assert result.size == file_create_data["size"]
        assert result.owner_id == file_create_data["owner_id"]

    def test_update(
        self,
        mock_db: MagicMock,
        crud_file: CRUDFile,
        test_file: FileModel,
        file_update_data: dict,
    ):
        """Test updating a file."""
        # Arrange
        obj_in = FileUpdate(**file_update_data)

        # Act
        result = crud_file.update(mock_db, db_obj=test_file, obj_in=obj_in)

        # Assert
        assert result == test_file
        assert test_file.filename == file_update_data["filename"]
        assert test_file.size == file_update_data["size"]
        mock_db.add.assert_called_once_with(test_file)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(test_file)

    def test_remove(
        self, mock_db: MagicMock, crud_file: CRUDFile, test_file: FileModel
    ):
        """Test removing a file."""
        # Configure the mock to return our test file when queried by ID
        mock_db.query.return_value.get.return_value = test_file

        # Act
        result = crud_file.remove(mock_db, id=test_file.id)

        # Assert
        assert result == test_file
        mock_db.delete.assert_called_once_with(test_file)
        mock_db.commit.assert_called_once()

    def test_remove_non_existing(
        self, mock_db: MagicMock, crud_file: CRUDFile
    ):
        """Test removing a non-existing file."""
        # Arrange
        mock_db.query.return_value.get.return_value = None

        # Act
        result = crud_file.remove(mock_db, id=999)

        # Assert
        assert result is None
        mock_db.query.return_value.get.assert_called_once_with(999)
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()
