from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import (BaseModel, ConfigDict, EmailStr, Field, model_serializer,
                      model_validator)


class Token(BaseModel):
    """Schema for OAuth2 token response."""

    access_token: str = Field(..., description="The access token for authentication")
    token_type: str = Field(
        default="bearer", description="The type of token, typically 'bearer'"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
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


class TokenData(BaseModel):
    """Schema for token data (used internally for authentication)."""

    username: Optional[str] = Field(
        default=None, description="The username extracted from the token"
    )

    model_config = ConfigDict(extra="ignore")  # Ignore extra fields in token data


class UserBase(BaseModel):
    """Base schema for user data."""

    email: EmailStr = Field(..., description="The user's email address")
    username: str = Field(
        ..., min_length=3, max_length=50, description="The user's username"
    )
    full_name: Optional[str] = Field(
        default=None, max_length=100, description="The user's full name"
    )
    is_active: bool = Field(
        default=True, description="Whether the user account is active"
    )
    is_superuser: bool = Field(
        default=False, description="Whether the user has superuser privileges"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None},
    )


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(
        ...,
        min_length=8,
        description="The user's password (will be hashed before storage)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "password": "securepassword123",
                "is_active": True,
                "is_superuser": False,
            }
        }
    )


class UserUpdate(BaseModel):
    """Schema for updating user data (all fields optional)."""

    email: Optional[EmailStr] = Field(
        default=None, description="The user's new email address"
    )
    username: Optional[str] = Field(
        default=None, min_length=3, max_length=50, description="The user's new username"
    )
    full_name: Optional[str] = Field(
        default=None, max_length=100, description="The user's full name"
    )
    password: Optional[str] = Field(
        default=None,
        min_length=8,
        description="The user's new password (will be hashed before storage)",
    )
    is_active: Optional[bool] = Field(
        default=None, description="Whether the user account is active"
    )
    is_superuser: Optional[bool] = Field(
        default=None, description="Whether the user has superuser privileges"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "new.email@example.com",
                "username": "newusername",
                "full_name": "New Name",
                "password": "newsecurepassword123",
            }
        }
    )


class UserInDBBase(BaseModel):
    """Base schema for user data stored in the database."""

    id: int = Field(..., description="The user's unique ID")
    email: EmailStr = Field(..., description="The user's email address")
    username: str = Field(..., description="The user's username")
    full_name: Optional[str] = Field(default=None, description="The user's full name")
    is_active: bool = Field(
        default=True, description="Whether the user account is active"
    )
    is_superuser: bool = Field(
        default=False, description="Whether the user has superuser privileges"
    )
    created_at: datetime = Field(..., description="When the user account was created")
    updated_at: datetime = Field(
        ..., description="When the user account was last updated"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
            }
        },
    )

    @model_serializer
    def serialize_model(self):
        # Custom serialization for the model
        data = self.model_dump()
        # Convert datetime fields to ISO format
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


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    """Schema for user data stored in the database (includes hashed password)."""

    hashed_password: str = Field(..., description="The user's hashed password")
