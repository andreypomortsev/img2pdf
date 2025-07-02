"""
Celery tasks for background processing.

These tasks act as stateless wrappers over the service layer logic.
"""

import logging
from typing import Any, Dict, List

from celery.app.task import Task
from celery.exceptions import MaxRetriesExceededError

from app.core.exceptions import ServiceError
from app.services.task_executor import TaskExecutorService
from app.services.task_service import task_service
from app.worker import celery_app

logger = logging.getLogger(__name__)


def _handle_task_failure(
    task: Task, exc: Exception, operation_name: str
) -> Dict[str, Any]:
    """Handle task failure with appropriate logging and retry logic."""
    retries = task.request.retries
    max_retries = task.max_retries or 3

    if isinstance(exc, ServiceError):
        # Business logic errors should not be retried
        logger.error("Service error in %s: %s", operation_name, str(exc))
        return {
            "status": "error",
            "error": str(exc),
            "retries": retries,
            "max_retries": max_retries,
        }

    if retries < max_retries:
        # Calculate backoff time with jitter
        countdown = min(60 * (retries + 1), 300)  # Max 5 min delay
        logger.warning(
            "Retrying %s (attempt %d/%d) in %ds: %s",
            operation_name,
            retries + 1,
            max_retries,
            countdown,
            str(exc),
        )
        try:
            raise task.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            logger.error(
                "Max retries (%d) exceeded for %s", max_retries, operation_name
            )

    # If we get here, we've exceeded max retries
    logger.error(
        "Task %s failed after %d retries: %s",
        operation_name,
        retries,
        str(exc),
        exc_info=True,
    )
    return {
        "status": "error",
        "error": f"Failed after {retries} retries: {str(exc)}",
        "retries": retries,
        "max_retries": max_retries,
    }


@celery_app.task(
    bind=True,
    name="convert_image_to_pdf",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=330,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
)
def convert_image_to_pdf(
    self: Task, file_id: int, owner_id: int
) -> Dict[str, Any]:
    """
    Celery task to convert an image file to PDF.

    Args:
        file_id: ID of the image file to convert
        owner_id: ID of the user who owns the file

    Returns:
        Dict containing status, file_id, and file_path on success
    """
    operation_name = f"Image to PDF conversion for file ID {file_id}"
    logger.info("Starting %s", operation_name)

    try:
        return TaskExecutorService.execute_with_retry(
            self,
            operation_name=operation_name,
            operation_func=task_service.convert_image_to_pdf,
            file_id=file_id,
            owner_id=owner_id,
        )
    except Exception as exc:
        return _handle_task_failure(self, exc, operation_name)


@celery_app.task(
    bind=True,
    name="merge_pdfs",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=600,
    time_limit=630,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def merge_pdfs(
    self: Task, file_ids: List[int], output_filename: str, owner_id: int
) -> Dict[str, Any]:
    """
    Celery task to merge multiple PDFs into a single PDF.

    Args:
        file_ids: List of file IDs to merge
        output_filename: Name for the merged PDF file
        owner_id: ID of the user who owns the files

    Returns:
        Dict containing status, file_id, and file_path on success
    """
    operation_name = f"Merge PDFs {file_ids} into {output_filename}"
    logger.info("Starting %s", operation_name)

    try:
        return TaskExecutorService.execute_with_retry(
            self,
            operation_name=operation_name,
            operation_func=task_service.merge_pdfs,
            file_ids=file_ids,
            output_filename=output_filename,
            owner_id=owner_id,
        )
    except Exception as exc:
        return _handle_task_failure(self, exc, operation_name)


@celery_app.task(name="test_task")
def test_task() -> str:
    """
    A simple test task to verify Celery worker is running.

    Returns:
        Status message
    """
    logger.info("Test task executed")
    return "Test task completed successfully"
