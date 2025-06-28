from datetime import datetime, timezone
from typing import Optional
from unittest.mock import ANY, MagicMock, patch

import pytest
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.crud.crud_user import (CRUDUser, authenticate_user, create_user,
                                get_user, get_user_by_email,
                                get_user_by_username, get_users, update_user)
from app.models.user import User
from app.schemas.token import UserCreate


class MockUserCreate(BaseModel):
    """Mock UserCreate schema for testing."""

    email: str
    username: str
    password: str
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


class MockUserUpdate(BaseModel):
    """Mock UserUpdate schema for testing."""

    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


@pytest.fixture
def mock_db():
    """Create a mock database session with proper query chaining."""
    # Create a mock for the query object
    query_mock = MagicMock()
    filter_mock = MagicMock()
    offset_mock = MagicMock()
    limit_mock = MagicMock()

    # Set up the chain: query -> filter -> first/all/offset/limit
    query_mock.filter.return_value = filter_mock
    filter_mock.first.return_value = None
    filter_mock.all.return_value = []
    filter_mock.offset.return_value = offset_mock
    offset_mock.limit.return_value = limit_mock
    limit_mock.all.return_value = []

    # Create the session mock
    db = MagicMock(spec=Session)
    db.query.return_value = query_mock

    # For direct model queries (like User.id == X)
    db.query.return_value.filter.return_value = filter_mock

    # For session.query(User).get(id)
    db.query.return_value.get.return_value = None

    # Add get method directly to the mock for get_user function
    db.get.return_value = None

    return db


@pytest.fixture
def test_user():
    """Create a test user instance."""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpass"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestCRUDUser:
    """Test cases for CRUDUser class."""

    def test_get_by_email_found(self, mock_db, test_user):
        """Test getting a user by email when user exists."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = test_user
        crud = CRUDUser(User)

        # Act
        result = crud.get_by_email(mock_db, email=test_user.email)

        # Assert
        assert result == test_user
        mock_db.query.assert_called_once_with(User)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_by_email_not_found(self, mock_db):
        """Test getting a user by email when user doesn't exist."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        crud = CRUDUser(User)

        # Act
        result = crud.get_by_email(mock_db, email="nonexistent@example.com")

        # Assert
        assert result is None
        mock_db.query.assert_called_once_with(User)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_by_username_found(self, mock_db, test_user):
        """Test getting a user by username when user exists."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = test_user
        crud = CRUDUser(User)

        # Act
        result = crud.get_by_username(mock_db, username=test_user.username)

        # Assert
        assert result == test_user
        mock_db.query.assert_called_once_with(User)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_by_username_not_found(self, mock_db):
        """Test getting a user by username when user doesn't exist."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        crud = CRUDUser(User)

        # Act
        result = crud.get_by_username(mock_db, username="nonexistent")

        # Assert
        assert result is None
        mock_db.query.assert_called_once_with(User)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_create_user(self, mock_db, test_user):
        """Test creating a new user."""
        # Arrange
        user_data = {
            "email": "new@example.com",
            "username": "newuser",
            "password": "newpassword123",  # At least 8 characters
            "full_name": "New User",
        }
        user_create = UserCreate(**user_data)

        # Mock the User model to return our test user
        with patch("app.crud.crud_user.User", return_value=test_user) as mock_user:
            crud = CRUDUser(User)

            # Act
            result = crud.create(mock_db, obj_in=user_create)

            # Assert
            assert result == test_user
            mock_user.assert_called_once_with(
                email=user_data["email"],
                username=user_data["username"],
                hashed_password=ANY,  # Password is hashed
                full_name=user_data["full_name"],
                is_active=True,  # Default value
                is_superuser=False,  # Default value
            )
            mock_db.add.assert_called_once_with(test_user)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(test_user)

    def test_authenticate_success(self, mock_db, test_user):
        """Test successful user authentication."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = test_user
        crud = CRUDUser(User)

        # Act
        result = crud.authenticate(
            mock_db,
            email=test_user.email,
            password="testpass",  # Matches the hashed password in test_user
        )

        # Assert
        assert result == test_user
        mock_db.query.assert_called_once_with(User)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_authenticate_wrong_password(self, mock_db, test_user):
        """Test authentication with wrong password."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = test_user
        crud = CRUDUser(User)

        # Act
        result = crud.authenticate(mock_db, email=test_user.email, password="wrongpass")

        # Assert
        assert result is None

    def test_authenticate_user_not_found(self, mock_db):
        """Test authentication when user doesn't exist."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        crud = CRUDUser(User)

        # Act
        result = crud.authenticate(
            mock_db, email="nonexistent@example.com", password="anypass"
        )

        # Assert
        assert result is None


class TestUserFunctions:
    """Test cases for standalone user functions."""

    def test_get_user(self, mock_db, test_user):
        """Test getting a user by ID."""
        # Arrange
        # Mock the query().filter().first() chain that get_user uses
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_first = MagicMock(return_value=test_user)

        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = test_user

        # Act
        result = get_user(mock_db, user_id=1)

        # Assert
        assert result == test_user
        mock_db.query.assert_called_once_with(User)
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()

    def test_get_user_by_email(self, mock_db, test_user):
        """Test getting a user by email."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = test_user

        # Act
        result = get_user_by_email(mock_db, email=test_user.email)

        # Assert
        assert result == test_user
        mock_db.query.assert_called_once_with(User)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_user_by_username(self, mock_db, test_user):
        """Test getting a user by username."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = test_user

        # Act
        result = get_user_by_username(mock_db, username=test_user.username)

        # Assert
        assert result == test_user
        mock_db.query.assert_called_once_with(User)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_users(self, mock_db, test_user):
        """Test getting a list of users with pagination."""
        # Arrange
        users = [test_user]
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = (
            users
        )

        # Act
        result = get_users(mock_db, skip=0, limit=10)

        # Assert
        assert result == users
        mock_db.query.assert_called_once_with(User)
        mock_db.query.return_value.offset.assert_called_once_with(0)
        mock_db.query.return_value.offset.return_value.limit.assert_called_once_with(10)
        mock_db.query.return_value.offset.return_value.limit.return_value.all.assert_called_once()

    def test_create_user_function(self, mock_db, test_user):
        """Test the standalone create_user function."""
        # Arrange
        user_data = {
            "email": "new@example.com",
            "username": "newuser",
            "password": "newpassword123",  # At least 8 characters
            "full_name": "New User",
            "is_active": True,
            "is_superuser": False,
        }
        user_create = UserCreate(**user_data)

        # Mock the User model to return our test user
        with patch("app.crud.crud_user.User", return_value=test_user) as mock_user:
            # Act
            result = create_user(mock_db, user=user_create)

            # Assert
            assert result == test_user
            mock_user.assert_called_once_with(
                email=user_data["email"],
                username=user_data["username"],
                hashed_password=ANY,  # Password is hashed
                full_name=user_data["full_name"],
                is_active=user_data["is_active"],
                is_superuser=user_data["is_superuser"],
            )
            mock_db.add.assert_called_once_with(test_user)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(test_user)

    def test_update_user_with_dict(self, mock_db, test_user):
        """Test updating a user with a dictionary."""
        # Arrange
        update_data = {"email": "updated@example.com", "full_name": "Updated Name"}

        # Act
        result = update_user(mock_db, db_user=test_user, user_in=update_data)

        # Assert
        assert result == test_user
        assert test_user.email == update_data["email"]
        assert test_user.full_name == update_data["full_name"]
        mock_db.add.assert_called_once_with(test_user)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(test_user)

    def test_update_user_with_password(self, mock_db, test_user):
        """Test updating a user's password."""
        # Arrange
        update_data = {"password": "newpassword"}

        # Act
        result = update_user(mock_db, db_user=test_user, user_in=update_data)

        # Assert
        assert result == test_user
        assert test_user.hashed_password != "newpassword"  # Should be hashed
        assert verify_password("newpassword", test_user.hashed_password)
        mock_db.add.assert_called_once_with(test_user)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(test_user)

    def test_authenticate_user_success(self, mock_db, test_user):
        """Test successful user authentication with standalone function."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = test_user

        # Act
        result = authenticate_user(
            mock_db,
            username=test_user.username,
            password="testpass",  # Matches the hashed password in test_user
        )

        # Assert
        assert result == test_user
        mock_db.query.assert_called_once_with(User)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()

    def test_authenticate_user_wrong_password(self, mock_db, test_user):
        """Test authentication with wrong password using standalone function."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = test_user

        # Act
        result = authenticate_user(
            mock_db, username=test_user.username, password="wrongpass"
        )

        # Assert
        assert result is None

    def test_authenticate_user_not_found(self, mock_db):
        """Test authentication when user doesn't exist using standalone function."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = authenticate_user(mock_db, username="nonexistent", password="anypass")

        # Assert
        assert result is None


class TestUserInstance:
    """Test cases for the global user instance."""

    def test_user_instance(self):
        """Test that the global user instance is properly configured."""
        from app.crud.crud_user import user

        assert user.model == User
