"""Tests for the User model."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import get_password_hash, verify_password
from app.models.user import User


def test_user_creation(db_session):
    """Test creating a new user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.is_active is True
    assert user.is_superuser is False
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)
    assert verify_password("testpassword", user.hashed_password)


def test_user_email_uniqueness(db_session):
    """Test that user email must be unique."""
    # Create first user
    user1 = User(
        email="duplicate@example.com",
        username="user1",
        hashed_password=get_password_hash("password1"),
    )
    db_session.add(user1)
    db_session.commit()

    # Try to create user with same email but different username
    user2 = User(
        email="duplicate@example.com",
        username="user2",
        hashed_password=get_password_hash("password2"),
    )
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_username_uniqueness(db_session):
    """Test that username must be unique."""
    # Create first user
    user1 = User(
        email="user1@example.com",
        username="duplicate_username",
        hashed_password=get_password_hash("password1"),
    )
    db_session.add(user1)
    db_session.commit()

    # Try to create user with same username but different email
    user2 = User(
        email="user2@example.com",
        username="duplicate_username",
        hashed_password=get_password_hash("password2"),
    )
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_authentication():
    """Test user password verification."""
    password = "securepassword123"
    user = User(
        email="auth@example.com",
        username="authuser",
        hashed_password=get_password_hash(password),
    )

    assert verify_password(password, user.hashed_password) is True
    assert verify_password("wrongpassword", user.hashed_password) is False


def test_user_last_login(db_session):
    """Test updating user's last login timestamp."""
    user = User(
        email="login@example.com",
        username="loginuser",
        hashed_password=get_password_hash("test"),
    )
    db_session.add(user)
    db_session.commit()

    # Initial last_login should be None
    assert user.last_login is None

    # Update last_login
    login_time = datetime.now(timezone.utc)
    user.last_login = login_time
    db_session.commit()
    db_session.refresh(user)

    assert user.last_login is not None
    # Ensure both datetimes are timezone-aware before comparison
    last_login = (
        user.last_login.replace(tzinfo=timezone.utc)
        if user.last_login.tzinfo is None
        else user.last_login
    )
    assert abs((last_login - login_time).total_seconds()) < 1


def test_user_relationships(db_session, test_user):
    """Test relationships with other models."""
    from app.models.file import File

    # Create a file owned by the test user
    file = File(
        filename="test.txt",
        filepath="/uploads/test.txt",
        size=1024,
        content_type="text/plain",
        owner_id=test_user.id,
    )
    db_session.add(file)
    db_session.commit()

    # Test relationship
    assert len(test_user.files) == 1
    assert test_user.files[0].filename == "test.txt"
    assert test_user.files[0].owner == test_user
