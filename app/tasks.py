"""
Celery tasks for background processing.

This module contains task definitions that interface with the Celery worker.
Business logic is implemented in the service layer.
"""

import logging
from typing import Any, Dict, List

from app.db.session import get_db
from app.worker import celery_app

logger = logging.getLogger(__name__)


def _execute_with_db_retry(task_instance, operation_name, operation_func, *args, **kwargs):
    """
    Execute a database operation with retry logic.

    Args:
        task_instance: The Celery task instance
        operation_name: Name of the operation for logging
        operation_func: Function to execute
        *args: Positional arguments to pass to the operation function
        **kwargs: Keyword arguments to pass to the operation function

    Returns:
        The result of the operation function

    Raises:
        self.retry: If the operation fails and should be retried
    """
    db = next(get_db())
    try:
        logger.info("Starting %s", operation_name)
        result = operation_func(db, *args, **kwargs)
        logger.info("Completed %s successfully", operation_name)
        return result
    except Exception as exc:
        logger.error(
            "Error during %s: %s",
            operation_name,
            str(exc),
            exc_info=True,
        )
        # Retry with exponential backoff
        raise task_instance.retry(exc=exc, countdown=60 * task_instance.request.retries)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="convert_image_to_pdf",
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    soft_time_limit=300,  # 5 minutes
    time_limit=330,  # 5.5 minutes (must be > soft_time_limit)
)
def convert_image_to_pdf(self, file_id: int, owner_id: int) -> Dict[str, Any]:
    """
    Celery task to convert an image file to PDF.

    Args:
        file_id: ID of the image file to convert
        owner_id: ID of the user who owns the file

    Returns:
        dict: Status and result of the conversion
    """
    from app.services.pdf_service import pdf_service

    def _convert_image(db):
        pdf_file = pdf_service.convert_image_to_pdf(db, file_id, owner_id)
        return {
            "status": "success",
            "file_id": pdf_file.id,
            "file_path": pdf_file.filepath,
        }

    return _execute_with_db_retry(
        self,
        f"image to PDF conversion for file id {file_id}",
        _convert_image
    )


@celery_app.task(
    bind=True,
    name="merge_pdfs",
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    soft_time_limit=600,  # 10 minutes
    time_limit=630,  # 10.5 minutes (must be > soft_time_limit)
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,  # 5 minutes max backoff
    retry_jitter=True,
)
def merge_pdfs(
    self, file_ids: List[int], output_filename: str, owner_id: int
) -> Dict[str, Any]:
    """
    Celery task to merge multiple PDFs into a single PDF.

    Args:
        file_ids: List of file IDs to merge
        output_filename: Name of the output PDF file
        owner_id: ID of the user who owns the files

    Returns:
        dict: Status and result of the merge operation
    """
    from app.services.pdf_service import pdf_service

    def _merge_pdfs(db):
        merged_file = pdf_service.merge_pdfs(
            db, file_ids, output_filename, owner_id
        )
        return {
            "status": "success",
            "file_id": merged_file.id,
            "file_path": merged_file.filepath,
        }

    return _execute_with_db_retry(
        self,
        f"PDF merge for files {file_ids} into {output_filename}",
        _merge_pdfs
    )


@celery_app.task(name="test_task")
def test_task() -> str:
    """
    A simple test task to verify Celery worker is running.

    Returns:
        str: Test message
    """
    logger.info("Test task executed")
    return "Test task completed successfully"
