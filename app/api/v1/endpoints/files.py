from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.file_service import file_service
from app.tasks import convert_image_to_pdf
from app.worker import celery_app

router = APIRouter()


class TaskResponse(BaseModel):
    task_id: str


@router.post("/upload-image/", response_model=TaskResponse)
def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload an image file and start conversion to PDF.
    """
    db_file = file_service.save_file(db=db, file=file)
    task = convert_image_to_pdf.delay(db_file.id)
    return {"task_id": task.id}


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result,
    }
    return result
