import logging
import os

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.file_service import file_service
from app.tasks import convert_image_to_pdf
from app.worker import celery_app

router = APIRouter()
logger = logging.getLogger(__name__)


class TaskResponse(BaseModel):
    task_id: str
    file_id: int


@router.post("/upload-image/", response_model=TaskResponse)
def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload an image file and start conversion to PDF.
    """
    logger.info("Uploading file: %s", file.filename)

    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Only images are allowed.",
        )

    try:
        db_file = file_service.save_file(db=db, file=file)

        # Flush the session to get an ID for the file object
        db.flush()

        # Dispatch Celery task for PDF conversion
        task = convert_image_to_pdf.delay(db_file.id)
        logger.info("Created conversion task %s for file %s", task.id, file.filename)
        return {"task_id": task.id, "file_id": db_file.id}
    except Exception as e:
        logger.error("Error uploading file %s: %s", file.filename, e, exc_info=True)
        raise


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    logger.info("Checking status for task %s", task_id)
    task_result = AsyncResult(task_id, app=celery_app)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result,
    }
    logger.info("Task %s status: %s", task_id, task_result.status)
    return result


@router.get("/files/{file_id}/download")
def download_file(file_id: int, db: Session = Depends(get_db)):
    """
    Download a file from the filesystem.
    """
    logger.info("Downloading file with id %s", file_id)
    db_file = file_service.get_file_by_id(db=db, file_id=file_id)
    if not db_file:
        logger.error("File with id %s not found for download.", file_id)
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.exists(db_file.filepath):
        logger.error("File not found on disk at path: %s", db_file.filepath)
        raise HTTPException(status_code=404, detail="File not found on disk")

    logger.info(
        "File %s found, preparing for download from %s.",
        db_file.filename,
        db_file.filepath,
    )
    return FileResponse(path=db_file.filepath, filename=db_file.filename)
