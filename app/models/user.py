"""Database models for user authentication and authorization.

This module contains the SQLAlchemy models for handling user accounts,
authentication, and authorization within the application.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import get_password_hash, verify_password
from app.db.base import Base
from app.db.mixins import TimestampMixin


class User(Base, TimestampMixin):
    """Database model for application users.

    Attributes:
        id: Primary key
        email: User's email address (unique)
        username: Username (unique)
        hashed_password: Hashed password (never store plain text passwords!)
        full_name: User's full name
        is_active: Whether the user account is active
        is_superuser: Whether the user has superuser privileges
        last_login: Timestamp of the user's last login
        files: Relationship to files uploaded by the user

    Inherited from TimestampMixin:
        created_at: Timestamp when the user was created
        updated_at: Timestamp when the user was last updated
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="User's email address (must be unique)",
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Username (must be unique)",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Hashed password (never store plain text passwords!)",
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="User's full name"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Whether the user account is active"
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether the user has superuser privileges",
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, comment="Timestamp of the user's last login"
    )

    # Relationships
    files: Mapped[List["File"]] = relationship(
        "File", back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.username} (ID: {self.id})>"

    def set_password(self, password: str) -> None:
        """Set the user's password.

        Args:
            password: The plain text password to hash and store
        """
        self.hashed_password = get_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the stored hash.

        Args:
            password: The plain text password to verify

        Returns:
            bool: True if the password is correct, False otherwise
        """
        return verify_password(password, self.hashed_password)

    @property
    def is_authenticated(self) -> bool:
        """Check if the user is authenticated."""
        return True  # All users with an account are considered authenticated

    @property
    def is_anonymous(self) -> bool:
        """Check if the user is anonymous."""
        return False  # We don't have anonymous users in this model

    def get_id(self) -> str:
        """Get the user ID as a string (required by Flask-Login and similar)."""
        return str(self.id)
