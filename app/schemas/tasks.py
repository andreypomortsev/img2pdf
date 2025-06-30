from pydantic import BaseModel


class TaskResponse(BaseModel):
    task_id: str
    file_id: int
