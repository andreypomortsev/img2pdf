import logging
import os
import uuid
from pathlib import Path
from typing import Generator, List

import img2pdf
from PyPDF2 import PdfMerger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db as get_db_session
from app.models.file import File
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="test_task")
def test_task(self):
    """A simple test task to verify eager execution."""
    logger.info("Test task executed")
    return "Test task completed"


TEMP_DIR = Path("tmp")


def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.
    This is a simple wrapper around the get_db dependency.
    """
    db = next(get_db_session())
    try:
        yield db
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="convert_image_to_pdf",
    autoretry_for=(ValueError,),
    max_retries=5,
    retry_backoff=True,
)
def convert_image_to_pdf(self, file_id: int) -> int:
    """
    Converts an image file on the filesystem to a PDF.
    The new PDF is stored as a new file on disk and a new record in the database.
    """
    logger.info("Starting image to PDF conversion for file id %s", file_id)

    db = next(get_db())
    try:
        image_file = db.query(File).filter(File.id == file_id).first()
        if not image_file:
            logger.error("File with id %s not found.", file_id)
            raise ValueError(f"File with id {file_id} not found.")

        logger.info("Converting image %s to PDF.", image_file.filepath)

        with open(image_file.filepath, "rb") as f:
            pdf_bytes = img2pdf.convert([f.read()])
        logger.info(
            "Successfully converted image %s to PDF in memory.",
            image_file.filename,
        )

        pdf_filename = os.path.splitext(image_file.filename)[0] + ".pdf"
        output_dir = Path(image_file.filepath).parent
        pdf_filepath = output_dir / pdf_filename

        with open(pdf_filepath, "wb") as f:
            f.write(pdf_bytes)

        logger.info("Saved new PDF to %s", pdf_filepath)

        new_pdf_file = File(filename=pdf_filename, filepath=str(pdf_filepath))
        db.add(new_pdf_file)
        db.commit()
        db.refresh(new_pdf_file)
        logger.info(
            "Saved new PDF record for original file id %s as new file id %s",
            file_id,
            new_pdf_file.id,
        )

        return new_pdf_file.id
    except Exception as e:
        logger.error(
            "Error converting image to PDF for file id %s: %s",
            file_id,
            e,
            exc_info=True,
        )
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="merge_pdfs",
    autoretry_for=(ValueError,),
    max_retries=5,
    retry_backoff=True,
)
def merge_pdfs(self, file_ids: List[int], output_filename: str) -> int:
    """
    Merges multiple PDF files from the filesystem into a single PDF.
    The merged PDF is stored as a new file on disk and a new record in
    the database.
    """
    logger.info("Starting PDF merge for files %s", file_ids)
    merger = PdfMerger()  # Initialize merger before try block
    db = next(get_db())

    try:
        # Get all input files
        pdf_files = db.query(File).filter(File.id.in_(file_ids)).all()
        if len(pdf_files) != len(file_ids):
            found_ids = {f.id for f in pdf_files}
            missing_ids = set(file_ids) - found_ids
            raise ValueError(f"Files with ids {missing_ids} not found.")

        # Ensure output directory exists
        output_dir = Path(pdf_files[0].filepath).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename

        # Merge PDFs
        for pdf_file in pdf_files:
            merger.append(pdf_file.filepath)

        # Write merged PDF to disk
        merger.write(str(output_path))

        # Create a new file record for the merged PDF
        merged_file = File(filename=output_filename, filepath=str(output_path))
        db.add(merged_file)
        db.commit()
        db.refresh(merged_file)

        logger.info(
            "Successfully merged %d PDFs into %s with id %s",
            len(pdf_files),
            output_path,
            merged_file.id,
        )

        return merged_file.id

    except Exception as e:
        logger.exception("Error merging PDFs. Exception: %s", e)
        raise
    finally:
        merger.close()
