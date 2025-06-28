"""Database models for file storage and management.

This module contains the SQLAlchemy models for handling file uploads,
metadata, and relationships with users.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class File(Base):
    """Database model for uploaded files.

    Attributes:
        id: Primary key
        filename: Original filename
        filepath: Path where the file is stored
        content_type: MIME type of the file
        size: File size in bytes
        owner_id: Foreign key to the user who uploaded the file
        created_at: Timestamp when the file was uploaded
        updated_at: Timestamp when the file was last updated
        is_deleted: Flag indicating if the file is soft-deleted
        deleted_at: Timestamp when the file was soft-deleted
        owner: Relationship to the User model
    """

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    filepath: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # File size in bytes
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="files")

    def delete(self) -> None:
        """Soft delete the file."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<File {self.filename} (ID: {self.id})>"

    @property
    def url(self) -> Optional[str]:
        """Get the URL to access the file."""
        if not self.filepath:
            return None
        # This would be replaced with your actual file URL logic
        return f"/files/{self.id}"
