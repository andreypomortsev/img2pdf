from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class FileBase(BaseModel):
    """Base schema for File model."""

    filename: str
    content_type: Optional[str] = None
    size: Optional[int] = None


class FileCreate(FileBase):
    """Schema for creating a new file."""

    filepath: str
    owner_id: Optional[int] = None


class FileUpdate(BaseModel):
    """Schema for updating a file."""

    filename: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None


class FileInDBBase(FileBase):
    """Base schema for File in database."""

    id: int
    owner_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class File(FileInDBBase):
    """Schema for File model with additional computed properties."""

    url: Optional[HttpUrl] = None


class FileInDB(FileInDBBase):
    """Schema for File in database with all fields."""

    filepath: str
