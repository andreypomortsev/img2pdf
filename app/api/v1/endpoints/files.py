import logging
import os
from typing import List

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud
from app.api import deps
from app.db.session import get_db
from app.models.file import File as FileModel
from app.models.user import User
from app.schemas.file import File as FileSchema
from app.services.file_service import file_service
from app.tasks import convert_image_to_pdf
from app.worker import celery_app

router = APIRouter()
logger = logging.getLogger(__name__)


class TaskResponse(BaseModel):
    task_id: str
    file_id: int


@router.post("/upload-image/", response_model=TaskResponse)
def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Upload an image file and start conversion to PDF.
    Requires authentication.
    """
    logger.info("Uploading file: %s for user: %s", file.filename, current_user.email)

    if not file.content_type.startswith("image/"):
        detail = f"Unsupported file type: {file.content_type}."
        raise HTTPException(
            status_code=400,
            detail=detail,
        )

    try:
        # Save the file with owner information
        db_file = file_service.save_file(
            db=db, file=file, owner_id=current_user.id, content_type=file.content_type
        )

        # Commit the session to make the file object available to the worker
        db.commit()

        # Dispatch Celery task for PDF conversion
        task = convert_image_to_pdf.delay(db_file.id)
        logger.info(
            "Created conversion task %s for file %s (user_id: %s)",
            task.id,
            file.filename,
            current_user.id,
        )
        return {"task_id": task.id, "file_id": db_file.id}
    except Exception as e:
        logger.error("Error uploading file %s: %s", file.filename, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload file")


@router.get(
    "/task/{task_id}",
    responses={
        200: {"description": "Task status retrieved successfully"},
        401: {"description": "Unauthorized - Invalid authentication credentials"},
        403: {"description": "Forbidden - Not authorized to access this task"},
        404: {"description": "Not Found - Task not found"},
    },
)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Check the status of a Celery task.

    This endpoint allows users to check the status of their file conversion tasks.
    Users can only check the status of their own tasks.
    """
    task_result = AsyncResult(task_id, app=celery_app)

    # If task is ready, verify the user has access to the result
    if (
        task_result.ready()
        and task_result.result
        and isinstance(task_result.result, dict)
    ):
        file_id = task_result.result.get("file_id")
        if file_id:
            db_file = crud.file.get(db, id=file_id)
            if (
                db_file
                and db_file.owner_id != current_user.id
                and not current_user.is_superuser
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this task",
                )

    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None,
    }
    logger.info("Task %s status: %s", task_id, task_result.status)


@router.get(
    "/{file_id}",
    response_class=FileResponse,
    responses={
        200: {"description": "File downloaded successfully"},
        401: {"description": "Unauthorized - Invalid authentication credentials"},
        403: {"description": "Forbidden - Not authorized to access this file"},
        404: {"description": "Not Found - File not found"},
    },
)
async def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Download a file.

    This endpoint allows users to download files they own.
    Superusers can download any file.
    """
    db_file = crud.file.get(db, id=file_id)
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Check if the current user is the owner or a superuser
    if db_file.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this file",
        )

    if not os.path.exists(db_file.filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk",
        )

    return FileResponse(
        db_file.filepath,
        media_type=db_file.content_type or "application/octet-stream",
        filename=db_file.filename or f"file_{file_id}",
    )


@router.get(
    "/",
    response_model=List[FileSchema],
    responses={
        200: {"description": "List of user's files"},
        401: {"description": "Unauthorized - Invalid authentication credentials"},
    },
)
async def list_files(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    List all files for the current user.

    This endpoint returns a paginated list of files owned by the current user.
    Superusers can see all files.
    """
    if current_user.is_superuser:
        files = db.query(FileModel).offset(skip).limit(limit).all()
    else:
        files = (
            db.query(FileModel)
            .filter(FileModel.owner_id == current_user.id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    return files
