from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.v1.endpoints.files import TaskResponse
from app.tasks import merge_pdfs

router = APIRouter()


class MergePdfsRequest(BaseModel):
    file_ids: List[int]
    output_filename: str


@router.post("/merge/", response_model=TaskResponse)
def merge_pdfs_endpoint(request: MergePdfsRequest):
    """
    Merge multiple PDF files into a single file.
    """
    task = merge_pdfs.delay(request.file_ids, request.output_filename)
    return {"task_id": task.id}
