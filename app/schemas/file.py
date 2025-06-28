from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "filename": "example.pdf",
                "content_type": "application/pdf",
                "size": 1024,
                "owner_id": 1,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
            }
        },
    )

    def model_dump_json(self, **kwargs):
        # Override to customize JSON serialization
        return super().model_dump_json(
            **{
                **kwargs,
                "exclude_unset": True,
                "by_alias": True,
            }
        )

    def model_dump(self, **kwargs):
        # Customize dict serialization for datetime fields
        data = super().model_dump(**kwargs)
        for field in ["created_at", "updated_at"]:
            if field in data and data[field] is not None:
                data[field] = data[field].isoformat()
        return data

    @model_validator(mode="before")
    @classmethod
    def set_timestamps(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Set timestamps if not provided."""
        if not isinstance(data, dict):
            return data

        now = datetime.now(timezone.utc)
        if "created_at" not in data or data["created_at"] is None:
            data["created_at"] = now
        if "updated_at" not in data or data["updated_at"] is None:
            data["updated_at"] = now
        return data


class File(FileInDBBase):
    """Schema for File model with additional computed properties."""

    url: Optional[HttpUrl] = Field(default=None, description="URL to access the file")

    @model_validator(mode="before")
    @classmethod
    def set_url(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Set the URL for the file if not provided."""
        if not isinstance(data, dict):
            return data

        if "url" not in data and "id" in data:
            data["url"] = f"/files/{data['id']}"
        return data


class FileInDB(FileInDBBase):
    """Schema for File in database with all fields."""

    filepath: str
