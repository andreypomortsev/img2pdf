from datetime import datetime

from pydantic import BaseModel


class FileBase(BaseModel):
    filename: str


class FileCreate(FileBase):
    filepath: str


class File(FileBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
