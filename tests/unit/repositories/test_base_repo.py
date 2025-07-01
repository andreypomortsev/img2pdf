"""Tests for the BaseRepository class."""

# Mock model for testing
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from pydantic import BaseModel
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.repositories.base import BaseRepository


class MockModel(Base):
    __tablename__ = "mock_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# Mock schema for testing
class MockModelCreate(BaseModel):
    name: str
    value: int


class MockModelUpdate(BaseModel):
    name: str | None = None
    value: int | None = None


@pytest_asyncio.fixture
async def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest_asyncio.fixture
async def base_repository(mock_db_session):
    """Create a BaseRepository instance with a mock model and session."""
    return BaseRepository(model=MockModel, db_session=mock_db_session)


class TestBaseRepository:
    """Test cases for BaseRepository."""

    @pytest.mark.asyncio
    async def test_get_found(self, base_repository, mock_db_session):
        """Test getting a record by ID when it exists."""
        # Setup
        test_id = 1
        mock_obj = MockModel(id=test_id, name="Test", value=42)

        # Configure the mock to return our test object
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_obj
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await base_repository.get(id=test_id)

        # Verify
        assert result == mock_obj
        mock_db_session.execute.assert_awaited_once()

        # Verify the query was built correctly
        args, _ = mock_db_session.execute.call_args
        assert str(args[0].whereclause) == "mock_models.id = :id_1"
        assert args[0].whereclause.right.value == test_id

    @pytest.mark.asyncio
    async def test_get_not_found(self, base_repository, mock_db_session):
        """Test getting a record by ID when it doesn't exist."""
        # Setup - return None to simulate not found
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await base_repository.get(id=999)

        # Verify
        assert result is None
        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_multi(self, base_repository, mock_db_session):
        """Test getting multiple records with pagination."""
        # Setup
        skip = 10
        limit = 5
        mock_objects = [
            MockModel(id=i, name=f"Test {i}", value=i * 10)
            for i in range(1, 6)
        ]

        # Configure the mock to return our test objects
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_objects
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await base_repository.get_multi(skip=skip, limit=limit)

        # Verify
        assert result == mock_objects
        mock_db_session.execute.assert_awaited_once()

        # Verify the query was built with correct pagination
        args, _ = mock_db_session.execute.call_args
        # The offset and limit might be applied to the query object directly
        # rather than as attributes, so we'll check the compiled SQL instead
        compiled = args[0].compile()
        assert "LIMIT :param_1" in str(compiled)
        assert "OFFSET :param_2" in str(compiled)

    @pytest.mark.asyncio
    async def test_create(self, base_repository, mock_db_session):
        """Test creating a new record."""
        # Setup
        obj_in = MockModelCreate(name="Test", value=42)

        # Execute
        result = await base_repository.create(obj_in=obj_in)

        # Verify the object was added to the session
        mock_db_session.add.assert_called_once()
        added_obj = mock_db_session.add.call_args[0][0]

        # Verify the object has the correct attributes
        assert isinstance(added_obj, MockModel)
        assert added_obj.name == obj_in.name
        assert added_obj.value == obj_in.value

        # Verify the session was committed and refreshed
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(added_obj)

        # The method should return the created object
        assert result == added_obj

    @pytest.mark.asyncio
    async def test_update_with_model(self, base_repository, mock_db_session):
        """Test updating a record with a Pydantic model."""
        # Setup
        db_obj = MockModel(id=1, name="Old Name", value=10)
        update_data = MockModelUpdate(name="New Name", value=20)

        # Execute
        result = await base_repository.update(
            db_obj=db_obj, obj_in=update_data
        )

        # Verify the object was updated
        assert db_obj.name == "New Name"
        assert db_obj.value == 20

        # Verify the session was committed and refreshed
        mock_db_session.add.assert_called_once_with(db_obj)
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(db_obj)

        # The method should return the updated object
        assert result == db_obj

    @pytest.mark.asyncio
    async def test_update_with_dict(self, base_repository, mock_db_session):
        """Test updating a record with a dictionary."""
        # Setup
        db_obj = MockModel(id=1, name="Old Name", value=10)
        update_data = {"name": "New Name", "value": 20}

        # Execute
        result = await base_repository.update(
            db_obj=db_obj, obj_in=update_data
        )

        # Verify the object was updated
        assert db_obj.name == "New Name"
        assert db_obj.value == 20

        # Verify the session was committed and refreshed
        mock_db_session.add.assert_called_once_with(db_obj)
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(db_obj)

        # The method should return the updated object
        assert result == db_obj

    @pytest.mark.asyncio
    async def test_update_partial(self, base_repository, mock_db_session):
        """Test partial update of a record."""
        # Setup - only update the name
        db_obj = MockModel(id=1, name="Old Name", value=10)
        update_data = {"name": "New Name"}  # Only update name

        # Execute
        result = await base_repository.update(
            db_obj=db_obj, obj_in=update_data
        )

        # Verify only the name was updated, value remains the same
        assert db_obj.name == "New Name"
        assert db_obj.value == 10

        # Verify the session was committed and refreshed
        mock_db_session.add.assert_called_once_with(db_obj)
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(db_obj)

        # The method should return the updated object
        assert result == db_obj

    @pytest.mark.asyncio
    async def test_remove_found(self, base_repository, mock_db_session):
        """Test removing an existing record."""
        # Setup
        test_id = 1
        mock_obj = MockModel(id=test_id, name="Test", value=42)

        # Mock get to return our test object
        with patch.object(
            base_repository, "get", return_value=mock_obj
        ) as mock_get:
            # Execute
            result = await base_repository.remove(id=test_id)

            # Verify get was called with the correct ID
            # The method is called with positional args, not keyword args
            mock_get.assert_awaited_once()
            assert mock_get.await_args[0] == (
                test_id,
            )  # Check positional args
            assert mock_get.await_args[1] == {}  # No keyword args

            # Verify the object was deleted and session was committed
            mock_db_session.delete.assert_called_once_with(mock_obj)
            mock_db_session.commit.assert_awaited_once()

            # The method should return the deleted object
            assert result == mock_obj

    @pytest.mark.asyncio
    async def test_remove_not_found(self, base_repository, mock_db_session):
        """Test removing a non-existent record."""
        # Setup - get returns None
        with patch.object(
            base_repository, "get", return_value=None
        ) as mock_get:
            # Execute
            result = await base_repository.remove(id=999)

            # Verify get was called with the correct ID
            # The method is called with positional args, not keyword args
            mock_get.assert_awaited_once()
            assert mock_get.await_args[0] == (999,)  # Check positional args
            assert mock_get.await_args[1] == {}  # No keyword args

            # Verify no delete or commit was called
            mock_db_session.delete.assert_not_called()
            mock_db_session.commit.assert_not_awaited()

            # The method should return None
            assert result is None
