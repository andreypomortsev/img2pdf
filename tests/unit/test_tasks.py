"""Unit tests for Celery tasks."""

from unittest.mock import MagicMock, patch

import pytest
from celery.exceptions import Retry

from app.core.exceptions import ServiceError
from app.tasks import _handle_task_failure, convert_image_to_pdf, merge_pdfs


class TestTaskHelpers:
    """Test helper functions for tasks."""

    def test_handle_task_failure_service_error(self):
        """Should handle service errors without retrying."""
        task = MagicMock()
        task.request.retries = 0
        task.max_retries = 3
        exc = ServiceError("Test error")

        result = _handle_task_failure(task, exc, "test_operation")

        assert result["status"] == "error"
        assert "Test error" in result["error"]
        assert result["retries"] == 0
        assert result["max_retries"] == 3
        task.retry.assert_not_called()

    def test_handle_task_failure_retryable(self):
        """Should handle retryable errors with backoff."""
        task = MagicMock()
        task.request.retries = 1
        task.max_retries = 3
        exc = Exception("Temporary failure")

        # Create a proper Retry exception
        retry_exc = Retry(exc=exc, when=120)
        task.retry.side_effect = retry_exc

        with pytest.raises(Retry) as exc_info:
            _handle_task_failure(task, exc, "test_operation")

        assert exc_info.value == retry_exc
        task.retry.assert_called_once_with(exc=exc, countdown=120)

    def test_handle_task_failure_max_retries(self):
        """Should handle max retries exceeded."""
        task = MagicMock()
        task.request.retries = 3
        task.max_retries = 3
        exc = Exception("Permanent failure")

        result = _handle_task_failure(task, exc, "test_operation")

        assert result["status"] == "error"
        assert "Failed after 3 retries" in result["error"]
        task.retry.assert_not_called()


class TestConvertImageToPdfTask:
    """Unit tests for convert_image_to_pdf Celery task."""

    @patch("app.tasks.TaskExecutorService.execute_with_retry", autospec=True)
    @patch("app.tasks.task_service.convert_image_to_pdf")
    def test_convert_image_to_pdf_success(self, mock_convert, mock_execute):
        """Task should delegate to TaskExecutorService and return expected result."""
        # Setup
        mock_result = {
            "status": "success",
            "file_id": 42,
            "file_path": "/files/42.pdf",
        }
        mock_execute.return_value = mock_result

        # Execute
        task = convert_image_to_pdf.s(file_id=1, owner_id=10)
        result = task.apply()

        # Verify
        assert result.get() == mock_result
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[1]
        assert call_args["file_id"] == 1
        assert call_args["owner_id"] == 10
        assert (
            "Image to PDF conversion for file ID 1"
            in call_args["operation_name"]
        )
        assert call_args["operation_func"] == mock_convert

    @patch("app.tasks.TaskExecutorService.execute_with_retry")
    def test_convert_image_to_pdf_failure(self, mock_execute):
        """Task should handle failures gracefully."""
        # Setup
        mock_execute.side_effect = Exception("Test error")

        # Execute
        task = convert_image_to_pdf.s(file_id=1, owner_id=10)
        result = task.apply()

        # Verify
        assert result.get()["status"] == "error"
        assert "Test error" in result.get()["error"]


class TestMergePdfsTask:
    """Unit tests for merge_pdfs Celery task."""

    @patch("app.tasks.TaskExecutorService.execute_with_retry", autospec=True)
    @patch("app.tasks.task_service.merge_pdfs")
    def test_merge_pdfs_success(self, mock_merge, mock_execute):
        """Task should delegate to TaskExecutorService and return expected result."""
        # Setup
        mock_result = {
            "status": "success",
            "file_id": 100,
            "file_path": "/files/merged.pdf",
        }
        mock_execute.return_value = mock_result

        # Execute
        task = merge_pdfs.s(
            file_ids=[1, 2, 3], output_filename="merged.pdf", owner_id=10
        )
        result = task.apply()

        # Verify
        assert result.get() == mock_result
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[1]
        assert call_args["file_ids"] == [1, 2, 3]
        assert call_args["output_filename"] == "merged.pdf"
        assert call_args["owner_id"] == 10
        assert (
            "Merge PDFs [1, 2, 3] into merged.pdf"
            in call_args["operation_name"]
        )
        assert call_args["operation_func"] == mock_merge

    @patch("app.tasks.TaskExecutorService.execute_with_retry")
    def test_merge_pdfs_failure(self, mock_execute):
        """Task should handle failures during PDF merging."""
        # Setup
        mock_execute.side_effect = Exception("Merge failed")

        # Execute
        task = merge_pdfs.s(
            file_ids=[1, 2, 3], output_filename="merged.pdf", owner_id=10
        )
        result = task.apply()

        # Verify
        assert result.get()["status"] == "error"
        assert "Merge failed" in result.get()["error"]
