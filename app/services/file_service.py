import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.file import File as FileModel
from app.tasks import merge_pdfs

logger = logging.getLogger(__name__)

TEMP_DIR = Path("tmp")


class FileService:
    def save_file(self, db: Session, file: UploadFile) -> FileModel:
        logger.info("Saving file: %s", file.filename)
        try:
            # Create a unique directory for the file
            unique_dir = TEMP_DIR / str(uuid.uuid4())
            unique_dir.mkdir(parents=True, exist_ok=True)
            filepath = unique_dir / file.filename

            # Read the file content and write it to the destination
            with open(filepath, "wb") as buffer:
                buffer.write(file.file.read())

            logger.info("File %s saved to %s", file.filename, filepath)

            db_file = FileModel(filename=file.filename, filepath=str(filepath))
            db.add(db_file)
            db.flush()
            db.refresh(db_file)
            logger.info(
                "File record for %s saved to database with id %s",
                file.filename,
                db_file.id,
            )
            return db_file
        except Exception as e:
            logger.error(
                "Error saving file %s: %s",
                file.filename,
                e,
                exc_info=True,
            )

            raise

    def get_file_by_id(self, db: Session, file_id: int) -> FileModel | None:
        logger.info("Fetching file with id %s from database", file_id)
        try:
            db_file = db.query(FileModel).filter(FileModel.id == file_id).first()
            if db_file:
                logger.info("File with id %s found: %s", file_id, db_file.filename)
            else:
                logger.warning("File with id %s not found in database", file_id)
            return db_file
        except Exception as e:
            logger.error(
                "Error fetching file %s from database: %s",
                file_id,
                e,
                exc_info=True,
            )
            raise

    def create_merge_task(self, file_ids: list[int], output_filename: str):
        logger.info(
            "Creating merge task for files %s into %s",
            file_ids,
            output_filename,
        )
        try:
            task = merge_pdfs.delay(file_ids, output_filename)
            logger.info("Created merge task %s", task.id)
            return task
        except Exception as e:
            logger.error(
                "Error creating merge task for files %s: %s",
                file_ids,
                e,
                exc_info=True,
            )
            raise


file_service = FileService()
