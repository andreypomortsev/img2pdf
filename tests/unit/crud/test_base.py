"""Tests for the base CRUD operations."""

from unittest.mock import MagicMock

import pytest


class TestCRUDBase:
    """Test cases for the base CRUD class."""

    def test_get_existing(self, db: MagicMock, test_crud, test_model):
        """Test retrieving an existing model by ID."""
        # Create a test instance
        expected_model = test_model(
            id=1, name="Test", description="Test Description"
        )
        db.query.return_value.filter.return_value.first.return_value = (
            expected_model
        )

        # Test getting the model by ID
        result = test_crud.get(db, id=1)

        # Verify the result and database interactions
        assert result == expected_model
        db.query.return_value.filter.assert_called_once()
        db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_non_existing(self, db: MagicMock, test_crud, test_model):
        """Test retrieving a non-existent model by ID."""
        # Configure the mock to return None (not found)
        db.query.return_value.filter.return_value.first.return_value = None

        # Test getting a non-existent model
        result = test_crud.get(db, id=999)

        # Verify the result and database interactions
        assert result is None
        db.query.return_value.filter.assert_called_once()
        db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_multi(self, db: MagicMock, test_crud, test_model):
        """Test retrieving multiple models with pagination."""
        # Create test data
        test_instances = [
            test_model(id=i, name=f"Test {i}") for i in range(1, 6)
        ]
        db.query.return_value.offset.return_value.limit.return_value.all.return_value = (
            test_instances
        )
        db.query.return_value.count.return_value = len(test_instances)

        # Test getting paginated results
        result = test_crud.get_multi(db, skip=10, limit=5)

        # Verify the result and database interactions
        assert result == test_instances
        db.query.return_value.offset.assert_called_once_with(10)
        db.query.return_value.offset.return_value.limit.assert_called_once_with(
            5
        )
        db.query.return_value.offset.return_value.limit.return_value.all.assert_called_once()

    def test_create(self, db: MagicMock, test_crud, test_schemas):
        """Test creating a new model."""
        # Get the create schema from fixtures
        TestCreateSchema, _ = test_schemas

        # Test data
        obj_in = TestCreateSchema(
            name="Test Model", description="A test model"
        )

        # Configure the mock to set the ID when an object is added
        def set_id(obj):
            obj.id = 1
            return obj

        db.add.side_effect = set_id

        # Test creating a new model
        result = test_crud.create(db, obj_in=obj_in)

        # Verify the result and database interactions
        assert result.id == 1
        assert result.name == "Test Model"
        assert result.description == "A test model"
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

        # Reset side effects
        db.add.side_effect = None

    def test_update_with_dict(self, db: MagicMock, test_crud, test_model):
        """Test updating a model with a dictionary."""
        # Create a test instance
        db_obj = test_model(
            id=1, name="Original Name", description="Original description"
        )

        # Update data
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
        }

        # Test updating the model
        result = test_crud.update(db, db_obj=db_obj, obj_in=update_data)

        # Verify the result and database interactions
        assert result == db_obj
        assert db_obj.name == "Updated Name"
        assert db_obj.description == "Updated description"
        db.add.assert_called_once_with(db_obj)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(db_obj)

    def test_update_with_schema(
        self, db: MagicMock, test_crud, test_model, test_schemas
    ):
        """Test updating a model with a Pydantic schema."""
        # Get the update schema from fixtures
        _, TestUpdateSchema = test_schemas

        # Create a test instance
        db_obj = test_model(
            id=1, name="Original Name", description="Original description"
        )

        # Create update data using schema
        update_data = TestUpdateSchema(
            name="Updated Name", description="Updated description"
        )

        # Test updating the model
        result = test_crud.update(db, db_obj=db_obj, obj_in=update_data)

        # Verify the result and database interactions
        assert result == db_obj
        assert db_obj.name == "Updated Name"
        assert db_obj.description == "Updated description"
        db.add.assert_called_once_with(db_obj)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(db_obj)

    def test_update_partial(self, db: MagicMock, test_crud, test_model):
        """Test partially updating a model."""
        # Create a test instance
        db_obj = test_model(
            id=1,
            name="Original Name",
            description="Original description",
            is_active=True,
        )

        # Partial update data (only name)
        update_data = {"name": "Updated Name"}

        # Test updating the model with partial data
        result = test_crud.update(db, db_obj=db_obj, obj_in=update_data)

        # Verify the result and database interactions
        assert result == db_obj
        assert db_obj.name == "Updated Name"
        assert (
            db_obj.description == "Original description"
        )  # Should remain unchanged
        assert db_obj.is_active is True  # Should remain unchanged
        db.add.assert_called_once_with(db_obj)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(db_obj)

    def test_remove(self, db: MagicMock, test_crud, test_model):
        """Test removing a model."""
        # Create a test instance
        test_instance = test_model(
            id=1, name="Test Model", description="To be deleted"
        )
        db.query.return_value.get.return_value = test_instance

        # Test removing the model
        result = test_crud.remove(db, id=1)

        # Verify the result and database interactions
        assert result == test_instance
        db.query.return_value.get.assert_called_once_with(1)
        db.delete.assert_called_once_with(test_instance)
        db.commit.assert_called_once()
        db.refresh.assert_not_called()

    def test_remove_non_existing(self, db: MagicMock, test_crud, test_model):
        """Test removing a non-existent model."""
        # Configure the mock to return None (not found)
        db.query.return_value.get.return_value = None

        # Test removing a non-existent model (should return None)
        result = test_crud.remove(db, id=999)

        # Verify the result and database interactions
        assert result is None
        db.query.return_value.get.assert_called_once_with(999)
        db.delete.assert_not_called()
        db.commit.assert_not_called()
        db.refresh.assert_not_called()

    def test_create_with_commit_error(
        self, db: MagicMock, test_crud, test_schemas
    ):
        """Test handling of commit error during model creation."""
        # Get the create schema from fixtures
        TestCreateSchema, _ = test_schemas

        # Test data that will cause a commit error
        obj_in = TestCreateSchema(
            name="Test Model",
            description="A test model that will fail to commit",
        )

        # Configure the mock to raise an exception on commit
        db.commit.side_effect = Exception("Database error")

        # Test that the exception is propagated
        with pytest.raises(Exception, match="Database error"):
            test_crud.create(db, obj_in=obj_in)

        # Verify cleanup was performed
        db.add.assert_called_once()
        db.rollback.assert_called_once()
        db.refresh.assert_not_called()

    def test_create_with_refresh_error(
        self, db: MagicMock, test_crud, test_schemas
    ):
        """Test handling of refresh error after successful commit."""
        # Get the create schema from fixtures
        TestCreateSchema, _ = test_schemas

        # Test data that will cause a refresh error
        obj_in = TestCreateSchema(
            name="Test Model",
            description="A test model that will fail to refresh",
        )

        # Configure the mock to raise an exception on refresh
        db.refresh.side_effect = Exception("Refresh failed")

        # Test that the exception is propagated
        with pytest.raises(Exception, match="Refresh failed"):
            test_crud.create(db, obj_in=obj_in)

        # Verify cleanup was performed
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.rollback.assert_called_once()  # Should rollback on refresh error

    def test_update_with_commit_error(
        self, db: MagicMock, test_crud, test_model
    ):
        """Test handling of commit error during model update."""
        # Create a test instance
        db_obj = test_model(
            id=1, name="Original Name", description="Test description"
        )

        # Update data that will cause a commit error
        update_data = {"name": "Updated Name"}
        db.commit.side_effect = Exception("Database error")

        # Test that the exception is propagated
        with pytest.raises(Exception, match="Database error"):
            test_crud.update(db, db_obj=db_obj, obj_in=update_data)

        # Verify cleanup was performed
        db.add.assert_called_once_with(db_obj)
        db.rollback.assert_called_once()
        db.refresh.assert_not_called()

    def test_update_with_none_values(
        self, db: MagicMock, test_crud, test_model
    ):
        """Test updating a model with None values in the update data."""
        # Create a test instance
        db_obj = test_model(
            id=1,
            name="Original Name",
            description="Original description",
            is_active=True,
        )

        # Update data with None values (should be ignored)
        update_data = {
            "name": None,  # Should be ignored
            "description": None,  # Should be ignored
            "is_active": None,  # Should be ignored
        }

        # Test updating the model with None values
        result = test_crud.update(db, db_obj=db_obj, obj_in=update_data)

        # Verify the result and database interactions
        assert result == db_obj
        assert db_obj.name == "Original Name"  # Should remain unchanged
        assert (
            db_obj.description == "Original description"
        )  # Should remain unchanged
        assert db_obj.is_active is True  # Should remain unchanged
        db.add.assert_called_once_with(db_obj)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(db_obj)

    def test_remove_with_commit_error(
        self, db: MagicMock, test_crud, test_model
    ):
        """Test handling of commit error during model removal."""
        # Create a test instance
        test_instance = test_model(
            id=1, name="Test Model", description="To be deleted"
        )
        db.query.return_value.get.return_value = test_instance
        db.commit.side_effect = Exception("Database error")

        # Test that the exception is propagated
        with pytest.raises(Exception, match="Database error"):
            test_crud.remove(db, id=1)

        # Verify cleanup was performed
        db.query.return_value.get.assert_called_once_with(1)
        db.delete.assert_called_once_with(test_instance)
        db.rollback.assert_called_once()  # Should rollback on commit error
