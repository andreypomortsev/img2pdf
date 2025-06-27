from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.security import get_password_hash, verify_password
from app.db.base import Base


class User(Base):
    """Database model for application users.

    Attributes:
        id: Primary key
        email: User's email address (unique)
        username: Username (unique)
        hashed_password: Hashed password (never store plain text passwords!)
        full_name: User's full name
        is_active: Whether the user account is active
        is_superuser: Whether the user has superuser privileges
        created_at: Timestamp when the user was created
        updated_at: Timestamp when the user was last updated
        files: Relationship to files uploaded by the user
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")

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
