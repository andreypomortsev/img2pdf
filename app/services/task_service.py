"""
Service layer responsible for task-specific operations.
Delegates to appropriate services for actual implementation.
"""

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.core.exceptions import ServiceError
from app.interfaces.task_service_interface import TaskServiceInterface
from app.services import pdf_service

logger = logging.getLogger(__name__)


class TaskService(TaskServiceInterface):
    """Service class for task-specific operations."""

    def convert_image_to_pdf(
        self, db: Session, file_id: int, owner_id: int
    ) -> Dict[str, Any]:
        """Convert an image to PDF using the PDF service."""
        try:
            pdf_file = pdf_service.convert_image_to_pdf(db, file_id, owner_id)
            return {
                "status": "success",
                "file_id": pdf_file.id,
                "file_path": pdf_file.filepath,
            }
        except Exception as e:
            logger.error(
                "Failed to convert image to PDF: %s", str(e), exc_info=True
            )
            raise ServiceError(
                f"Failed to convert image to PDF: {str(e)}"
            ) from e

    def merge_pdfs(
        self,
        db: Session,
        file_ids: List[int],
        output_filename: str,
        owner_id: int,
    ) -> Dict[str, Any]:
        """Merge multiple PDFs using the PDF service."""
        try:
            merged_file = pdf_service.merge_pdfs(
                db, file_ids, output_filename, owner_id
            )
            return {
                "status": "success",
                "file_id": merged_file.id,
                "file_path": merged_file.filepath,
            }
        except Exception as e:
            logger.error("Failed to merge PDFs: %s", str(e), exc_info=True)
            raise ServiceError(f"Failed to merge PDFs: {str(e)}") from e


# Singleton instance
task_service = TaskService()
