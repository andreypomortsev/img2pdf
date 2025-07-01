"""
Service responsible for executing long-running tasks with DB access.
Handles database sessions, retries, and error handling for background tasks.
"""

import logging
from contextlib import contextmanager
from typing import Callable, Generator, TypeVar

from celery.app.task import Task
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseError, ServiceError
from app.db.session import get_db

logger = logging.getLogger(__name__)
T = TypeVar("T")


class TaskExecutorService:
    """
    Service responsible for running operations that require DB access.
    Handles database sessions, retries, and error handling for background tasks.
    """

    @classmethod
    @contextmanager
    def db_session(cls) -> Generator[Session, None, None]:
        """Context manager for database sessions with proper cleanup."""
        db: Session = next(get_db())
        try:
            yield db
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error: %s", str(e), exc_info=True)
            raise DatabaseError(f"Database operation failed: {str(e)}")
        finally:
            db.close()

    @classmethod
    def execute_with_retry(
        cls,
        task_instance: Task,
        operation_name: str,
        operation_func: Callable[..., T],
        max_retries: int = 3,
        **kwargs,
    ) -> T:
        """
        Execute an operation with retry logic for transient failures.

        Args:
            task_instance: The Celery task instance
            operation_name: Human-readable name for the operation (for logging)
            operation_func: The function to execute
            max_retries: Maximum number of retry attempts
            **kwargs: Arguments to pass to operation_func

        Returns:
            The result of the operation

        Raises:
            ServiceError: For business logic errors (not retried)
            DatabaseError: For database errors (retried)
            Exception: For other unexpected errors (retried)
        """
        try:
            with cls.db_session() as db:
                logger.info("Starting %s", operation_name)
                result = operation_func(db=db, **kwargs)
                logger.info("Completed %s successfully", operation_name)
                return result

        except ServiceError as exc:
            # Business logic errors should not be retried
            logger.error(
                "Service error during %s: %s", operation_name, str(exc)
            )
            raise

        except DatabaseError as exc:
            # Database errors should be retried
            logger.error(
                "Database error during %s (will retry): %s",
                operation_name,
                str(exc),
            )
            raise task_instance.retry(
                exc=exc,
                countdown=min(
                    60 * (task_instance.request.retries or 1), 300
                ),  # Max 5 min delay
                max_retries=max_retries,
            )

        except Exception as exc:
            # Other unexpected errors should be retried
            logger.error(
                "Unexpected error during %s (will retry): %s",
                operation_name,
                str(exc),
                exc_info=True,
            )
            raise task_instance.retry(
                exc=exc,
                countdown=min(
                    60 * (task_instance.request.retries or 1), 300
                ),  # Max 5 min delay
                max_retries=max_retries,
            )
