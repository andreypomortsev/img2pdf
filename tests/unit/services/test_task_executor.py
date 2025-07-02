"""Unit tests for task_executor.py."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import DatabaseError, ServiceError
from app.services.task_executor import TaskExecutorService


class TestTaskExecutorService:
    """Test cases for TaskExecutorService."""

    @patch("app.services.task_executor.get_db")
    def test_db_session_success(self, mock_get_db):
        """Test db_session context manager with successful execution."""
        # Setup mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])

        # Test the context manager
        with TaskExecutorService.db_session() as db:
            assert db is mock_db
            # No commit should happen inside the context manager
            mock_db.commit.assert_not_called()

        # Verify the session was closed
        mock_db.close.assert_called_once()

    @patch("app.services.task_executor.get_db")
    @patch("app.services.task_executor.logger")
    def test_db_session_with_error(self, mock_logger, mock_get_db):
        """Test db_session context manager with database error."""
        # Create a mock database session
        mock_db = MagicMock()

        # Make get_db return an iterator that yields our mock_db
        mock_get_db.return_value = iter([mock_db])

        # Create a real SQLAlchemyError
        db_error = SQLAlchemyError("DB error")

        # Set up the mock to raise the error when query() is called
        mock_db.query.side_effect = db_error

        # Test that DatabaseError is raised when a database operation is performed
        with pytest.raises(DatabaseError, match="Database operation failed"):
            with TaskExecutorService.db_session() as db:
                # This will trigger the side_effect on mock_db.query()
                db.query()

        # Verify rollback was called and session was closed
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()

        # Verify error was logged with the correct format string and error message
        mock_logger.error.assert_called_once()
        # Check the format string and that the error message contains the expected text
        args = mock_logger.error.call_args[0]
        assert (
            len(args) >= 2
        ), "Expected at least 2 arguments in logger.error call"
        assert args[0] == "Database error: %s"
        assert "DB error" in str(args[1])

        # Verify rollback was called and session was closed
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()

        # Verify error was logged with the correct format string and error message
        mock_logger.error.assert_called_once()
        # Check the format string and that the error message contains the expected text
        args = mock_logger.error.call_args[0]
        assert (
            len(args) >= 2
        ), "Expected at least 2 arguments in logger.error call"
        assert args[0] == "Database error: %s"
        assert "DB error" in str(args[1])

    @patch("app.services.task_executor.TaskExecutorService.db_session")
    def test_execute_with_retry_success(self, mock_db_session):
        """Test execute_with_retry with successful execution."""
        # Setup mocks
        mock_task = MagicMock()
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # Mock operation function
        def mock_operation(db, x, y):
            return x + y

        # Test the method
        result = TaskExecutorService.execute_with_retry(
            task_instance=mock_task,
            operation_name="test_operation",
            operation_func=mock_operation,
            x=2,
            y=3,
        )

        # Verify the result and that no retry was attempted
        assert result == 5
        mock_task.retry.assert_not_called()

    @patch("app.services.task_executor.TaskExecutorService.db_session")
    def test_execute_with_retry_service_error(self, mock_db_session):
        """Test execute_with_retry with ServiceError (should not retry)."""
        # Setup mocks
        mock_task = MagicMock()
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # Mock operation that raises ServiceError
        def mock_operation(db):
            raise ServiceError("Business error")

        # Test that ServiceError is re-raised
        with pytest.raises(ServiceError, match="Business error"):
            TaskExecutorService.execute_with_retry(
                task_instance=mock_task,
                operation_name="test_operation",
                operation_func=mock_operation,
            )

        # Verify no retry was attempted
        mock_task.retry.assert_not_called()

    @patch("app.services.task_executor.TaskExecutorService.db_session")
    @patch("app.services.task_executor.logger")
    def test_execute_with_retry_database_error(
        self, mock_logger, mock_db_session
    ):
        """Test execute_with_retry with DatabaseError (should retry)."""
        # Setup mocks
        mock_task = MagicMock()
        # Configure request.retries to return a fixed value
        mock_task.request.retries = 0
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # Mock operation that raises DatabaseError
        def mock_operation(db):
            raise DatabaseError("DB error")

        # Configure retry to raise an exception to simulate Celery's behavior
        retry_exception = Exception("Retry")
        mock_task.retry.side_effect = retry_exception

        # Test that retry is called and the exception is propagated
        with pytest.raises(Exception, match="Retry"):
            TaskExecutorService.execute_with_retry(
                task_instance=mock_task,
                operation_name="test_operation",
                operation_func=mock_operation,
            )

        # Verify retry was called with correct parameters
        mock_task.retry.assert_called_once()
        retry_call_args = mock_task.retry.call_args[1]
        assert retry_call_args["max_retries"] == 3
        assert retry_call_args["countdown"] == 60  # min(60 * (0 + 1), 300)

        # Verify logging
        mock_logger.error.assert_called_once()
        # Check the format string and arguments
        assert (
            mock_logger.error.call_args[0][0]
            == "Database error during %s (will retry): %s"
        )
        assert mock_logger.error.call_args[0][1] == "test_operation"
        # The error message should be a string, not the exception object
        assert "DB error" in mock_logger.error.call_args[0][2]

    @patch("app.services.task_executor.TaskExecutorService.db_session")
    @patch("app.services.task_executor.logger")
    def test_execute_with_retry_unexpected_error(
        self, mock_logger, mock_db_session
    ):
        """Test execute_with_retry with unexpected error (should retry)."""
        # Setup mocks
        mock_task = MagicMock()
        # Configure request.retries to return a fixed value
        mock_task.request.retries = 0
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # Mock operation that raises an unexpected error
        def mock_operation(db):
            raise ValueError("Unexpected error")

        # Configure retry to raise an exception to simulate Celery's behavior
        retry_exception = Exception("Retry")
        mock_task.retry.side_effect = retry_exception

        # Test that retry is called and the exception is propagated
        with pytest.raises(Exception, match="Retry"):
            TaskExecutorService.execute_with_retry(
                task_instance=mock_task,
                operation_name="test_operation",
                operation_func=mock_operation,
            )

        # Verify retry was called with correct parameters
        mock_task.retry.assert_called_once()
        retry_call_args = mock_task.retry.call_args[1]
        assert retry_call_args["max_retries"] == 3
        assert retry_call_args["countdown"] == 60  # min(60 * (0 + 1), 300)

        # Verify logging
        mock_logger.error.assert_called_once()
        # Check the format string and arguments separately
        assert (
            mock_logger.error.call_args[0][0]
            == "Unexpected error during %s (will retry): %s"
        )
        assert mock_logger.error.call_args[0][1] == "test_operation"
        assert "Unexpected error" in str(mock_logger.error.call_args[0][2])

    @patch("app.services.task_executor.TaskExecutorService.db_session")
    @patch("app.services.task_executor.logger")
    def test_execute_with_retry_custom_max_retries(
        self, mock_logger, mock_db_session
    ):
        """Test execute_with_retry with custom max_retries parameter."""
        # Setup mocks
        mock_task = MagicMock()
        # Configure request.retries to return a fixed value
        mock_task.request.retries = 0
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # Mock operation that raises an error
        def mock_operation(db):
            raise DatabaseError("DB error")

        # Configure retry to raise an exception to simulate Celery's behavior
        retry_exception = Exception("Retry")
        mock_task.retry.side_effect = retry_exception

        # Test with custom max_retries
        with pytest.raises(Exception, match="Retry"):
            TaskExecutorService.execute_with_retry(
                task_instance=mock_task,
                operation_name="test_operation",
                operation_func=mock_operation,
                max_retries=5,
            )

        # Verify custom max_retries was used
        mock_task.retry.assert_called_once()
        retry_call_args = mock_task.retry.call_args[1]
        assert retry_call_args["max_retries"] == 5

        # Verify logging
        mock_logger.error.assert_called_once()
        # Check the format string and arguments
        assert (
            mock_logger.error.call_args[0][0]
            == "Database error during %s (will retry): %s"
        )
        assert mock_logger.error.call_args[0][1] == "test_operation"
        # The error message should be a string, not the exception object
        assert "DB error" in mock_logger.error.call_args[0][2]
