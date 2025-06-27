from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

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
        owner: Relationship to the User model
    """

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), index=True, nullable=False)
    filepath = Column(Text, nullable=False)
    content_type = Column(String(100), nullable=True)
    size = Column(Integer, nullable=True)  # File size in bytes
    owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="files")

    def __repr__(self) -> str:
        return f"<File {self.filename} (ID: {self.id})>"

    @property
    def url(self) -> Optional[str]:
        """Get the URL to access the file."""
        if not self.filepath:
            return None
        # This would be replaced with your actual file URL logic
        return f"/files/{self.id}"
