"""Pydantic schemas for task-related request/response models.

This module defines the data models used for task-related API responses,
ensuring consistent data structure and validation.
"""

from pydantic import BaseModel


class TaskResponse(BaseModel):
    """Response model for task operations.

    Attributes:
        task_id: A unique identifier for the background task.
        file_id: The ID of the file associated with the task.
    """

    task_id: str
    file_id: int
