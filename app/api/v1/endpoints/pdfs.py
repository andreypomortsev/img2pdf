import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud
from app.api import deps
from app.db.session import get_db
from app.models.file import File as FileModel
from app.models.user import User
from app.services.file_service import file_service

router = APIRouter()
logger = logging.getLogger(__name__)


class MergePdfsRequest(BaseModel):
    file_ids: List[int]
    output_filename: str


class MergeTaskResponse(BaseModel):
    task_id: str


@router.post(
    "/merge/",
    response_model=MergeTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Accepted - PDF merge task started"},
        400: {"description": "Bad Request - Invalid file IDs or other request error"},
        401: {"description": "Unauthorized - Invalid authentication credentials"},
        403: {"description": "Forbidden - Not authorized to access one or more files"},
        404: {"description": "Not Found - One or more files not found"},
    },
)
def merge_pdfs_endpoint(
    request: MergePdfsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Merge multiple PDF files into a single file.

    This endpoint allows users to merge multiple PDF files they own into a single PDF.
    Users must have read access to all specified files.
    """
    logger.info(
        "User %s creating merge task for files %s into %s",
        current_user.id,
        request.file_ids,
        request.output_filename,
    )

    # Verify the user has access to all files
    files = []
    for file_id in request.file_ids:
        db_file = crud.file.get(db, id=file_id)
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with ID {file_id} not found",
            )

        # Check if the current user is the owner or a superuser
        if db_file.owner_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to access file with ID {file_id}",
            )

        files.append(db_file)

    try:
        task = file_service.create_merge_task(
            file_ids=request.file_ids,
            output_filename=request.output_filename,
        )
        logger.info(
            "Created merge task %s for user %s",
            task.id,
            current_user.id,
        )
        # Commit the session to make the file objects available to the worker
        db.commit()
        return {"task_id": task.id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Error creating merge task for user %s: %s",
            current_user.id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the merge task",
        )
