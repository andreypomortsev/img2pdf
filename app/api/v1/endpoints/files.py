import logging
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import deps
from app.db.session import get_db
from app.models.user import User
from app.schemas.file import File as FileSchema
from app.services.file_service import file_service

router = APIRouter()
logger = logging.getLogger(__name__)


class TaskResponse(BaseModel):
    task_id: str
    file_id: int


@router.post("/upload-image/", response_model=TaskResponse)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Upload an image file and start conversion to PDF.
    
    This endpoint is idempotent - uploading the same file multiple times will create
    separate file entries and conversion tasks, ensuring no side effects from retries.
    """
    return file_service.start_image_conversion(db, file, current_user)


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
    
    This endpoint is idempotent - multiple identical requests will return the same result
    without any side effects.
    
    Users can only check the status of their own tasks. Superusers can check any task.
    """
    return file_service.get_task_status(task_id, db, current_user)


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
    
    This endpoint is idempotent - multiple identical requests will return the same file
    without any side effects.
    
    Users can only download their own files. Superusers can download any file.
    """
    db_file = file_service.get_file_by_id(db, file_id, current_user)
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
    
    This endpoint is idempotent - multiple identical requests will return the same
    list of files without any side effects.
    
    Regular users see only their own files. Superusers see all files.
    """
    return file_service.list_user_files(db, current_user, skip, limit)
