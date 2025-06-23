import logging
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.file_service import file_service

router = APIRouter()
logger = logging.getLogger(__name__)


class MergePdfsRequest(BaseModel):
    file_ids: List[int]
    output_filename: str


class MergeTaskResponse(BaseModel):
    task_id: str


@router.post("/merge/", response_model=MergeTaskResponse)
def merge_pdfs_endpoint(request: MergePdfsRequest, db: Session = Depends(get_db)):
    """
    Merge multiple PDF files into a single file.
    """
    logger.info(
        "Creating merge task for files %s into %s",
        request.file_ids,
        request.output_filename,
    )
    try:
        task = file_service.create_merge_task(
            file_ids=request.file_ids, output_filename=request.output_filename
        )
        logger.info("Created merge task %s", task.id)
        db.flush()
        return {"task_id": task.id}
    except Exception as e:
        logger.error(
            "Error creating merge task for files %s: %s",
            request.file_ids,
            e,
            exc_info=True,
        )
        raise
