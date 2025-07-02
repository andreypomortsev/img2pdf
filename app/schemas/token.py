from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    """Schema for OAuth2 token response."""

    access_token: str = Field(
        ..., description="The access token for authentication"
    )
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

    model_config = ConfigDict(extra="ignore")
