"""Tests for the base CRUD operations."""

from unittest import mock
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import Session, declarative_base

from app.crud.base import CRUDBase

# Create a separate base for tests to avoid table redefinition issues
TestBase = declarative_base()


# Create a test SQLAlchemy model
class TestModel(TestBase):
    """Test model for CRUD operations."""

    __tablename__ = "test_model"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    def __init__(self, **kwargs):
        # Initialize SQLAlchemy model
        super().__init__()
        # Set attributes from kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


# Create Pydantic models for testing
class TestCreateSchema(BaseModel):
    """Schema for creating a test model."""

    name: str
    description: str = ""
    is_active: bool = True


class TestUpdateSchema(BaseModel):
    """Schema for updating a test model."""

    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class TestCRUD(CRUDBase[TestModel, TestCreateSchema, TestUpdateSchema]):
    """Test CRUD class for testing base functionality."""

    pass


@pytest.fixture
def db() -> MagicMock:
    """Create a mock database session with proper return values."""
    mock_db = MagicMock(spec=Session)
    # Configure default return values for common methods
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.query.return_value.get.return_value = None
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = (
        []
    )
    return mock_db


@pytest.fixture
def test_crud() -> TestCRUD:
    """Create a test CRUD instance."""
    return TestCRUD(TestModel)


class TestCRUDBase:
    """Test cases for the base CRUD class."""

    def test_get_existing(self, db: MagicMock, test_crud: TestCRUD):
        """Test retrieving an existing model by ID."""
        # Arrange
        test_id = 1
        expected_model = TestModel()
        db.query.return_value.filter.return_value.first.return_value = (
            expected_model
        )

        # Act
        result = test_crud.get(db, id=test_id)

        # Assert
        assert result == expected_model
        db.query.assert_called_once_with(TestModel)
        db.query.return_value.filter.assert_called_once()
        db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_non_existing(self, db: MagicMock, test_crud: TestCRUD):
        """Test retrieving a non-existent model by ID."""
        # Arrange
        test_id = 999
        db.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = test_crud.get(db, id=test_id)

        # Assert
        assert result is None
        db.query.assert_called_once_with(TestModel)
        db.query.return_value.filter.assert_called_once()
        db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_multi(self, db: MagicMock, test_crud: TestCRUD):
        """Test retrieving multiple models with pagination."""
        # Arrange
        skip = 10
        limit = 5
        expected_models = [TestModel() for _ in range(5)]
        db.query.return_value.offset.return_value.limit.return_value.all.return_value = (
            expected_models
        )

        # Act
        result = test_crud.get_multi(db, skip=skip, limit=limit)

        # Assert
        assert result == expected_models
        db.query.assert_called_once_with(TestModel)
        db.query.return_value.offset.assert_called_once_with(skip)
        db.query.return_value.offset.return_value.limit.assert_called_once_with(
            limit
        )
        db.query.return_value.offset.return_value.limit.return_value.all.assert_called_once()

    def test_create(self, db: MagicMock, test_crud: TestCRUD):
        """Test creating a new model."""
        # Arrange
        obj_in = TestCreateSchema(
            name="Test Model", description="A test model"
        )
        db.add.return_value = None
        db.commit.return_value = None
        db.refresh.return_value = None

        # Create a real instance for comparison
        expected_obj = TestModel()
        expected_obj.id = 1
        expected_obj.name = "Test Model"
        expected_obj.description = "A test model"

        # Mock the model instantiation to return our test instance
        with mock.patch.object(
            TestModel, "__new__", return_value=expected_obj
        ):
            # Act
            result = test_crud.create(db, obj_in=obj_in)

        # Assert
        assert result is expected_obj
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(expected_obj)

    def test_update_with_dict(self, db: MagicMock, test_crud: TestCRUD):
        """Test updating a model with a dictionary."""
        # Arrange
        db_obj = TestModel()
        db_obj.id = 1
        db_obj.name = "Original Name"
        db_obj.description = "Original description"
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
        }

        # Act
        result = test_crud.update(db, db_obj=db_obj, obj_in=update_data)

        # Assert
        assert result == db_obj
        assert db_obj.name == update_data["name"]
        assert db_obj.description == update_data["description"]
        db.add.assert_called_once_with(db_obj)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(db_obj)

    def test_update_with_schema(self, db: MagicMock, test_crud: TestCRUD):
        """Test updating a model with a Pydantic schema."""
        # Arrange
        db_obj = TestModel()
        db_obj.id = 1
        db_obj.name = "Original Name"
        db_obj.description = "Original description"
        update_data = TestUpdateSchema(
            name="Updated Name", description="Updated description"
        )

        # Act
        result = test_crud.update(db, db_obj=db_obj, obj_in=update_data)

        # Assert
        assert result == db_obj
        assert db_obj.name == update_data.name
        assert db_obj.description == update_data.description
        db.add.assert_called_once_with(db_obj)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(db_obj)

    def test_update_partial(self, db: MagicMock, test_crud: TestCRUD):
        """Test partially updating a model."""
        # Arrange
        db_obj = TestModel()
        db_obj.id = 1
        db_obj.name = "Original Name"
        db_obj.description = "Original description"
        original_name = db_obj.name
        update_data = {"description": "Updated description"}

        # Act
        result = test_crud.update(db, db_obj=db_obj, obj_in=update_data)

        # Assert
        assert result == db_obj
        assert db_obj.name == original_name  # Should not change
        assert db_obj.description == update_data["description"]
        db.add.assert_called_once_with(db_obj)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(db_obj)

    def test_remove(self, db: MagicMock, test_crud: TestCRUD):
        """Test removing a model."""
        # Arrange
        test_id = 1
        db_obj = TestModel()
        db_obj.id = test_id
        db.query.return_value.get.return_value = db_obj

        # Act
        result = test_crud.remove(db, id=test_id)

        # Assert
        assert result == db_obj
        db.query.assert_called_once_with(TestModel)
        db.query.return_value.get.assert_called_once_with(test_id)
        db.delete.assert_called_once_with(db_obj)
        db.commit.assert_called_once()

    def test_remove_non_existing(self, db: MagicMock, test_crud: TestCRUD):
        """Test removing a non-existent model."""
        # Arrange
        test_id = 999
        db.query.return_value.get.return_value = None

        # Act
        result = test_crud.remove(db, id=test_id)

        # Assert
        assert result is None
        db.query.assert_called_once_with(TestModel)
        db.query.return_value.get.assert_called_once_with(test_id)
        # Should not call delete or commit when object not found
        db.delete.assert_not_called()
        db.commit.assert_not_called()

    def test_create_with_commit_error(
        self, db: MagicMock, test_crud: TestCRUD
    ):
        """Test handling of commit error during model creation."""
        # Arrange
        obj_in = TestCreateSchema(
            name="Test Model", description="A test model"
        )
        db.commit.side_effect = Exception("Database error")

        # Create a real instance for the mock to return
        mock_obj = TestModel()
        mock_obj.id = 1
        mock_obj.name = "Test Model"
        mock_obj.description = "A test model"

        # Mock the model instantiation to return our test instance
        with mock.patch.object(TestModel, "__new__", return_value=mock_obj):
            # Act & Assert
            with pytest.raises(Exception, match="Database error"):
                test_crud.create(db, obj_in=obj_in)

            # Verify rollback was called on error
            db.rollback.assert_called_once()

    def test_create_with_refresh_error(
        self, db: MagicMock, test_crud: TestCRUD
    ):
        """Test handling of refresh error after successful commit."""
        # Arrange
        obj_in = TestCreateSchema(
            name="Test Model", description="A test model"
        )
        db.refresh.side_effect = Exception("Refresh error")

        # Create a real instance for the mock to return
        mock_obj = TestModel()
        mock_obj.id = 1
        mock_obj.name = "Test Model"
        mock_obj.description = "A test model"

        # Mock the model instantiation to return our test instance
        with mock.patch.object(TestModel, "__new__", return_value=mock_obj):
            # Act & Assert
            with pytest.raises(Exception, match="Refresh error"):
                test_crud.create(db, obj_in=obj_in)

            # Verify commit was called before refresh
            db.commit.assert_called_once()

    def test_update_with_commit_error(
        self, db: MagicMock, test_crud: TestCRUD
    ):
        """Test handling of commit error during model update."""
        # Arrange
        db_obj = TestModel()
        db_obj.id = 1
        db_obj.name = "Original"
        db_obj.description = "Original description"
        update_data = {"name": "Updated", "description": "Updated description"}
        db.commit.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            test_crud.update(db, db_obj=db_obj, obj_in=update_data)

        # Verify rollback was called on error
        db.rollback.assert_called_once()

    def test_update_with_none_values(self, db: MagicMock, test_crud: TestCRUD):
        """Test updating a model with None values in the update data."""
        # Arrange
        db_obj = TestModel()
        db_obj.id = 1
        db_obj.name = "Original"
        db_obj.description = "Original description"
        update_data = {"name": None, "description": None}

        # Act
        result = test_crud.update(db, db_obj=db_obj, obj_in=update_data)

        # Assert
        assert result == db_obj
        # None values should not overwrite existing values
        assert db_obj.name == "Original"
        assert db_obj.description == "Original description"
        db.add.assert_called_once_with(db_obj)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(db_obj)

    def test_remove_with_commit_error(
        self, db: MagicMock, test_crud: TestCRUD
    ):
        """Test handling of commit error during model removal."""
        # Arrange
        test_id = 1
        db_obj = TestModel()
        db_obj.id = test_id
        db.query.return_value.get.return_value = db_obj
        db.commit.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            test_crud.remove(db, id=test_id)

        # Verify rollback was called on error
        db.rollback.assert_called_once()
