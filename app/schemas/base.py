"""Base schemas with common functionality."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, TypeVar

from pydantic import BaseModel, field_validator, model_validator

T = TypeVar("T", bound="BaseSchema")


class TimestampMixin(BaseModel):
    """Mixin for models with created_at and updated_at timestamps."""

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def ensure_tzinfo(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime has timezone info."""
        if v is None or v.tzinfo is not None:
            return v
        return v.replace(tzinfo=timezone.utc)

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

    def model_dump_json(self, **kwargs) -> str:
        """Override to customize JSON serialization."""
        return super().model_dump_json(
            **{
                **kwargs,
                "exclude_unset": True,
                "by_alias": True,
            }
        )

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Customize dict serialization for datetime fields."""
        data = super().model_dump(**kwargs)
        for field in ["created_at", "updated_at"]:
            if field in data and data[field] is not None:
                data[field] = data[field].isoformat()
        return data
