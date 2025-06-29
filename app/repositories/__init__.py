"""Repositories package for database operations.

This package contains repository classes that abstract database operations
for different domain models. Each repository provides a clean interface
for data access and encapsulates the query logic.
"""

from app.repositories.base import BaseRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
]
