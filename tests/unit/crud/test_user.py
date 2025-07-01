"""Tests for the CRUD user operations."""

from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.crud import crud_user
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def test_get_user():
    """Test retrieving a user by ID."""
    # Arrange
    db = MagicMock(spec=Session)
    user_id = 1
    expected_user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
    )
    db.query.return_value.filter.return_value.first.return_value = (
        expected_user
    )

    # Act
    result = crud_user.get_user(db, user_id)

    # Assert
    assert result == expected_user
    db.query.assert_called_once_with(User)
    db.query.return_value.filter.assert_called_once()
    db.query.return_value.filter.return_value.first.assert_called_once()


def test_get_user_not_found():
    """Test retrieving a non-existent user by ID."""
    # Arrange
    db = MagicMock(spec=Session)
    user_id = 999
    db.query.return_value.filter.return_value.first.return_value = None

    # Act
    result = crud_user.get_user(db, user_id)

    # Assert
    assert result is None
    db.query.assert_called_once_with(User)
    db.query.return_value.filter.assert_called_once()
    db.query.return_value.filter.return_value.first.assert_called_once()


def test_get_user_by_email():
    """Test retrieving a user by email."""
    # Arrange
    db = MagicMock(spec=Session)
    email = "test@example.com"
    expected_user = User(
        id=1,
        email=email,
        username="testuser",
        hashed_password="hashed_password",
    )
    db.query.return_value.filter.return_value.first.return_value = (
        expected_user
    )

    # Act
    result = crud_user.get_user_by_email(db, email)

    # Assert
    assert result == expected_user
    db.query.assert_called_once_with(User)
    db.query.return_value.filter.assert_called_once()
    db.query.return_value.filter.return_value.first.assert_called_once()


def test_get_user_by_username():
    """Test retrieving a user by username."""
    # Arrange
    db = MagicMock(spec=Session)
    username = "testuser"
    expected_user = User(
        id=1,
        email="test@example.com",
        username=username,
        hashed_password="hashed_password",
    )
    db.query.return_value.filter.return_value.first.return_value = (
        expected_user
    )

    # Act
    result = crud_user.get_user_by_username(db, username)

    # Assert
    assert result == expected_user
    db.query.assert_called_once_with(User)
    db.query.return_value.filter.assert_called_once()
    db.query.return_value.filter.return_value.first.assert_called_once()


def test_get_users():
    """Test retrieving a list of users with pagination."""
    # Arrange
    db = MagicMock(spec=Session)
    skip = 10
    limit = 5
    expected_users = [
        User(id=i, email=f"user{i}@example.com", username=f"user{i}")
        for i in range(1, 6)
    ]
    db.query.return_value.offset.return_value.limit.return_value.all.return_value = (
        expected_users
    )

    # Act
    result = crud_user.get_users(db, skip=skip, limit=limit)

    # Assert
    assert result == expected_users
    db.query.assert_called_once_with(User)
    db.query.return_value.offset.assert_called_once_with(skip)
    db.query.return_value.offset.return_value.limit.assert_called_once_with(
        limit
    )
    db.query.return_value.offset.return_value.limit.return_value.all.assert_called_once()


def test_create_user():
    """Test creating a new user."""
    # Arrange
    db = MagicMock(spec=Session)
    user_data = UserCreate(
        email="new@example.com",
        username="newuser",
        password="password123",
        full_name="New User",
    )
    expected_hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=expected_hashed_password,
        full_name=user_data.full_name,
        is_active=True,
        is_superuser=False,
    )
    db.add.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = None

    # Act
    result = crud_user.create_user(db, user_data)

    # Assert
    assert result.email == user_data.email
    assert result.username == user_data.username
    assert result.full_name == user_data.full_name
    assert result.is_active is True
    assert result.is_superuser is False
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


def test_update_user_with_dict():
    """Test updating a user with a dictionary."""
    # Arrange
    db = MagicMock(spec=Session)
    db_user = User(
        id=1,
        email="old@example.com",
        username="olduser",
        hashed_password="old_hashed_password",
        full_name="Old User",
    )
    update_data = {
        "email": "new@example.com",
        "username": "newuser",
        "full_name": "New User",
        "password": "newpassword123",
    }

    # Act
    result = crud_user.update_user(db, db_user, update_data)

    # Assert
    assert result.email == update_data["email"]
    assert result.username == update_data["username"]
    assert result.full_name == update_data["full_name"]
    assert (
        result.hashed_password != "old_hashed_password"
    )  # Password should be hashed
    assert (
        "password" not in result.__dict__
    )  # Password should be removed from update data
    db.add.assert_called_once_with(db_user)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(db_user)


def test_update_user_with_userupdate():
    """Test updating a user with a UserUpdate object."""
    # Arrange
    db = MagicMock(spec=Session)
    db_user = User(
        id=1,
        email="old@example.com",
        username="olduser",
        hashed_password="old_hashed_password",
        full_name="Old User",
    )
    update_data = UserUpdate(
        email="new@example.com",
        username="newuser",
        full_name="New User",
        password="newpassword123",
    )

    # Act
    result = crud_user.update_user(db, db_user, update_data)

    # Assert
    assert result.email == update_data.email
    assert result.username == update_data.username
    assert result.full_name == update_data.full_name
    assert (
        result.hashed_password != "old_hashed_password"
    )  # Password should be hashed
    assert (
        "password" not in result.__dict__
    )  # Password should be removed from update data
    db.add.assert_called_once_with(db_user)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(db_user)


def test_authenticate_user_success():
    """Test successful user authentication."""
    # Arrange
    db = MagicMock(spec=Session)
    username = "testuser"
    password = "password123"
    hashed_password = get_password_hash(password)
    expected_user = User(
        id=1,
        email="test@example.com",
        username=username,
        hashed_password=hashed_password,
    )
    db.query.return_value.filter.return_value.first.return_value = (
        expected_user
    )

    # Act
    result = crud_user.authenticate_user(
        db, username=username, password=password
    )

    # Assert
    assert result == expected_user
    db.query.assert_called_once_with(User)
    db.query.return_value.filter.assert_called_once()


def test_authenticate_user_invalid_username():
    """Test authentication with non-existent username."""
    # Arrange
    db = MagicMock(spec=Session)
    username = "nonexistent"
    db.query.return_value.filter.return_value.first.return_value = None

    # Act
    result = crud_user.authenticate_user(
        db, username=username, password="anypassword"
    )

    # Assert
    assert result is None
    db.query.assert_called_once_with(User)
    db.query.return_value.filter.assert_called_once()


def test_authenticate_user_invalid_password():
    """Test authentication with incorrect password."""
    # Arrange
    db = MagicMock(spec=Session)
    username = "testuser"
    hashed_password = get_password_hash("correctpassword")
    expected_user = User(
        id=1,
        email="test@example.com",
        username=username,
        hashed_password=hashed_password,
    )
    db.query.return_value.filter.return_value.first.return_value = (
        expected_user
    )

    # Act
    result = crud_user.authenticate_user(
        db, username=username, password="wrongpassword"
    )

    # Assert
    assert result is None
    db.query.assert_called_once_with(User)
    db.query.return_value.filter.assert_called_once()


class TestCRUDUser:
    """Test cases for the CRUDUser class methods."""

    def test_get_by_email(self):
        """Test retrieving a user by email using CRUDUser class."""
        # Arrange
        db = MagicMock(spec=Session)
        email = "test@example.com"
        expected_user = User(
            id=1,
            email=email,
            username="testuser",
            hashed_password="hashed_password",
        )
        db.query.return_value.filter.return_value.first.return_value = (
            expected_user
        )
        crud = crud_user.user

        # Act
        result = crud.get_by_email(db, email=email)

        # Assert
        assert result == expected_user
        db.query.assert_called_once_with(User)
        db.query.return_value.filter.assert_called_once()
        db.query.return_value.filter.return_value.first.assert_called_once()

    def test_get_by_username(self):
        """Test retrieving a user by username using CRUDUser class."""
        # Arrange
        db = MagicMock(spec=Session)
        username = "testuser"
        expected_user = User(
            id=1,
            email="test@example.com",
            username=username,
            hashed_password="hashed",
        )
        db.query.return_value.filter.return_value.first.return_value = (
            expected_user
        )
        crud = crud_user.user

        # Act
        result = crud.get_by_username(db, username=username)

        # Assert
        assert result == expected_user
        db.query.assert_called_once_with(User)
        db.query.return_value.filter.assert_called_once()
        db.query.return_value.filter.return_value.first.assert_called_once()

    def test_create(self):
        """Test creating a new user using CRUDUser class."""
        # Arrange
        db = MagicMock(spec=Session)
        user_data = UserCreate(
            email="new@example.com",
            username="newuser",
            password="password123",
            full_name="New User",
            is_active=True,
            is_superuser=False,
        )
        expected_hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=expected_hashed_password,
            full_name=user_data.full_name,
            is_active=user_data.is_active,
            is_superuser=user_data.is_superuser,
        )
        db.add.return_value = None
        db.commit.return_value = None
        db.refresh.return_value = None
        crud = crud_user.user

        # Act
        result = crud.create(db, obj_in=user_data)

        # Assert
        assert result.email == user_data.email
        assert result.username == user_data.username
        assert result.full_name == user_data.full_name
        assert result.is_active is user_data.is_active
        assert result.is_superuser is user_data.is_superuser
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_authenticate_success(self):
        """Test successful authentication using CRUDUser class."""
        # Arrange
        db = MagicMock(spec=Session)
        email = "test@example.com"
        password = "password123"
        hashed_password = get_password_hash(password)
        expected_user = User(
            id=1,
            email=email,
            username="testuser",
            hashed_password=hashed_password,
        )
        db.query.return_value.filter.return_value.first.return_value = (
            expected_user
        )
        crud = crud_user.user

        # Act
        result = crud.authenticate(db, email=email, password=password)

        # Assert
        assert result == expected_user
        db.query.assert_called_once_with(User)
        db.query.return_value.filter.assert_called_once()

    def test_authenticate_invalid_email(self):
        """Test authentication with non-existent email using CRUDUser class."""
        # Arrange
        db = MagicMock(spec=Session)
        email = "nonexistent@example.com"
        db.query.return_value.filter.return_value.first.return_value = None
        crud = crud_user.user

        # Act
        result = crud.authenticate(db, email=email, password="anypassword")

        # Assert
        assert result is None
        db.query.assert_called_once_with(User)
        db.query.return_value.filter.assert_called_once()

    def test_authenticate_invalid_password(self):
        """Test authentication with incorrect password using CRUDUser class."""
        # Arrange
        db = MagicMock(spec=Session)
        email = "test@example.com"
        hashed_password = get_password_hash("correctpassword")
        expected_user = User(
            id=1,
            email=email,
            username="testuser",
            hashed_password=hashed_password,
        )
        db.query.return_value.filter.return_value.first.return_value = (
            expected_user
        )
        crud = crud_user.user

        # Act
        result = crud.authenticate(db, email=email, password="wrongpassword")

        # Assert
        assert result is None
