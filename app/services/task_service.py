"""Service for handling task-related operations."""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.pdf import MergePdfsRequest, MergeTaskResponse
from app.tasks import merge_pdfs

logger = logging.getLogger(__name__)


class TaskService:
    """Service for handling task-related operations."""

    def create_merge_task(
        self,
        db: Session,
        request: MergePdfsRequest,
        current_user: User,
    ) -> MergeTaskResponse:
        """
        Create a task to merge multiple PDFs.

        Args:
            db: Database session
            request: The merge PDFs request
            current_user: The currently authenticated user

        Returns:
            MergeTaskResponse: The response containing the task ID

        Raises:
            HTTPException: If there's an error creating the task
        """
        try:
            # Create a Celery task for merging PDFs
            task = merge_pdfs.delay(
                file_ids=request.file_ids,
                output_filename=request.output_filename,
                owner_id=current_user.id,
            )

            # Log the task creation
            logger.info(
                "Created merge task %s for user %s",
                task.id,
                current_user.id,
            )

            # Return the task ID to track the task status
            return MergeTaskResponse(task_id=task.id)

        except Exception as e:
            logger.error(
                "Error creating merge task for user %s: %s",
                current_user.id,
                str(e),
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create merge task",
            ) from e


# Create a singleton instance
task_service = TaskService()
