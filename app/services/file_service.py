import os

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.file import File as FileModel


class FileService:
    def save_file(self, db: Session, file: UploadFile) -> FileModel:
        # Ensure the static/files directory exists
        os.makedirs("static/files", exist_ok=True)

        filepath = os.path.join("static/files", file.filename)
        with open(filepath, "wb") as buffer:
            buffer.write(file.file.read())

        db_file = FileModel(filename=file.filename, filepath=filepath)
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        return db_file


file_service = FileService()
