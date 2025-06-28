"""Tests for the UserRepository class."""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.token import UserCreate, UserUpdate


@pytest_asyncio.fixture
async def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest_asyncio.fixture
async def user_repository(mock_db_session):
    """Create a UserRepository instance with a mock session and model."""
    from app.models.user import User

    return UserRepository(model=User, db_session=mock_db_session)


class TestUserRepository:
    """Test cases for UserRepository."""

    @pytest.mark.asyncio
    async def test_get_by_email_found(self, user_repository, mock_db_session):
        """Test getting a user by email when user exists."""
        # Setup
        test_email = "test@example.com"
        mock_user = User(
            id=1,
            email=test_email,
            username="testuser",
            hashed_password="hashed_password",
            full_name="Test User",
            is_active=True,
        )

        # Configure the mock to return our test user
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_by_email(test_email)

        # Verify
        assert result == mock_user
        mock_db_session.execute.assert_awaited_once()

        # Verify the query was built correctly
        args, _ = mock_db_session.execute.call_args
        assert str(args[0].whereclause) == "users.email = :email_1"
        assert args[0].whereclause.right.value == test_email

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, user_repository, mock_db_session):
        """Test getting a user by email when user doesn't exist."""
        # Setup
        test_email = "nonexistent@example.com"
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_by_email(test_email)

        # Verify
        assert result is None
        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_username_found(self, user_repository, mock_db_session):
        """Test getting a user by username when user exists."""
        # Setup
        test_username = "testuser"
        mock_user = User(
            id=1,
            email="test@example.com",
            username=test_username,
            hashed_password="hashed_password",
            full_name="Test User",
            is_active=True,
        )

        # Configure the mock to return our test user
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_db_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_by_username(test_username)

        # Verify
        assert result == mock_user
        mock_db_session.execute.assert_awaited_once()

        # Verify the query was built correctly
        args, _ = mock_db_session.execute.call_args
        assert str(args[0].whereclause) == "users.username = :username_1"
        assert args[0].whereclause.right.value == test_username

    @pytest.mark.asyncio
    async def test_create_user(self, user_repository, mock_db_session):
        """Test creating a new user."""
        # Setup
        user_data = UserCreate(
            email="new@example.com",
            username="newuser",
            password="testpass123",
            full_name="New User",
            is_active=True,
            is_superuser=False,
        )

        # Mock the password hashing
        with patch("app.repositories.user_repository.get_password_hash") as mock_hash:
            mock_hash.return_value = "hashed_password"

            # Execute
            result = await user_repository.create(obj_in=user_data)

            # Verify
            mock_db_session.add.assert_called_once()
            added_user = mock_db_session.add.call_args[0][0]

            # Check user attributes
            assert added_user.email == user_data.email
            assert added_user.username == user_data.username
            assert added_user.hashed_password == "hashed_password"
            assert added_user.full_name == user_data.full_name
            assert added_user.is_active is True
            assert added_user.is_superuser is False

            # Verify the session was committed and refreshed
            mock_db_session.commit.assert_awaited_once()
            mock_db_session.refresh.assert_awaited_once_with(added_user)

            # The method should return the created user
            assert result == added_user

    @pytest.mark.asyncio
    async def test_authenticate_success(self, user_repository, mock_db_session):
        """Test successful user authentication."""
        # Setup
        username = "testuser"
        password = "testpass123"
        hashed_password = get_password_hash(password)

        mock_user = User(
            id=1,
            email="test@example.com",
            username=username,
            hashed_password=hashed_password,
            full_name="Test User",
            is_active=True,
        )

        # Mock get_by_username to return our test user
        with patch.object(user_repository, "get_by_username", return_value=mock_user):
            # Execute
            result = await user_repository.authenticate(
                username=username, password=password
            )

            # Verify
            assert result == mock_user

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, user_repository):
        """Test authentication with wrong password."""
        # Setup
        username = "testuser"
        mock_user = User(
            id=1,
            email="test@example.com",
            username=username,
            hashed_password=get_password_hash("correct_password"),
            full_name="Test User",
            is_active=True,
        )

        # Mock get_by_username to return our test user
        with patch.object(user_repository, "get_by_username", return_value=mock_user):
            # Execute with wrong password
            result = await user_repository.authenticate(
                username=username, password="wrong_password"
            )

            # Verify
            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, user_repository):
        """Test authentication when user doesn't exist."""
        # Setup - mock get_by_username to return None
        with patch.object(user_repository, "get_by_username", return_value=None):
            # Execute with non-existent user
            result = await user_repository.authenticate(
                username="nonexistent", password="anypassword"
            )

            # Verify
            assert result is None

    @pytest.mark.asyncio
    async def test_is_active(self, user_repository):
        """Test checking if a user is active."""
        # Test with active user
        active_user = User(is_active=True)
        assert await user_repository.is_active(active_user) is True

        # Test with inactive user
        inactive_user = User(is_active=False)
        assert await user_repository.is_active(inactive_user) is False

    @pytest.mark.asyncio
    async def test_is_superuser(self, user_repository):
        """Test checking if a user is a superuser."""
        # Test with superuser
        superuser = User(is_superuser=True)
        assert await user_repository.is_superuser(superuser) is True

        # Test with regular user
        regular_user = User(is_superuser=False)
        assert await user_repository.is_superuser(regular_user) is False
