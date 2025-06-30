"""Pydantic schemas for PDF-related operations."""

from typing import List

from pydantic import BaseModel


class MergePdfsRequest(BaseModel):
    """Request model for merging PDFs.

    Attributes:
        file_ids: List of file IDs to merge
        output_filename: Name for the merged output file
    """

    file_ids: List[int]
    output_filename: str


class MergeTaskResponse(BaseModel):
    """Response model for a merge task.

    Attributes:
        task_id: ID of the Celery task processing the merge
    """

    task_id: str
