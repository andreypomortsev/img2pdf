"""Database model mixins with common functionality."""

from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


def now_utc() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
        nullable=False,
        server_default=func.now(),
        server_onupdate=func.now(),
        comment="Timestamp when the record was last updated",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary with ISO format timestamps."""
        return {
            **{
                k: v for k, v in self.__dict__.items() if not k.startswith("_")
            },
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }
