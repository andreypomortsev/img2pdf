import io
import logging
import os
import uuid
from pathlib import Path
from typing import List

import celery
import img2pdf
from celery.utils.log import get_task_logger
from PyPDF2 import PdfMerger

from app.db.session import SessionLocal
from app.models.file import File as FileModel
from app.worker import celery_app

logger = logging.getLogger(__name__)

TEMP_DIR = Path("tmp")


@celery_app.task
def convert_image_to_pdf(file_id: int) -> int:
    """
    Converts an image file on the filesystem to a PDF.
    The new PDF is stored as a new file on disk and a new record in the database.
    """
    logger.info("Starting image to PDF conversion for file id %s", file_id)
    try:
        with SessionLocal() as db:
            image_file = db.query(FileModel).filter(FileModel.id == file_id).first()
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

            new_pdf_file = FileModel(filename=pdf_filename, filepath=str(pdf_filepath))
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
        raise


@celery_app.task(bind=True)
def merge_pdfs(self: celery.Task, file_ids: List[int], output_filename: str) -> int:
    """
    Merges multiple PDF files from the filesystem into a single PDF.
    The merged PDF is stored as a new file on disk and a new record in the database.
    """
    logger.info("Starting PDF merge for file ids %s into %s", file_ids, output_filename)
    merger = PdfMerger()
    try:
        with SessionLocal() as db:
            files = db.query(FileModel).filter(FileModel.id.in_(file_ids)).all()
            if len(files) != len(file_ids):
                found_ids = {file.id for file in files}
                missing_ids = set(file_ids) - found_ids
                logger.error("Could not find files with ids: %s", missing_ids)
                raise ValueError(f"Files with ids {list(missing_ids)} not found.")

            logger.info("Merging %d PDF files.", len(files))
            for db_file in files:
                merger.append(db_file.filepath)

            unique_dir = TEMP_DIR / str(uuid.uuid4())
            unique_dir.mkdir(parents=True, exist_ok=True)
            output_filepath = unique_dir / output_filename

            merger.write(str(output_filepath))

            logger.info("Saved merged PDF to %s", output_filepath)

            new_merged_file = FileModel(
                filename=output_filename, filepath=str(output_filepath)
            )
            db.add(new_merged_file)
            db.commit()
            db.refresh(new_merged_file)
            logger.info(
                "Saved new merged PDF record for file ids %s as new file id %s",
                file_ids,
                new_merged_file.id,
            )

            return new_merged_file.id
    except Exception as e:
        logger.error(
            "Error merging PDFs for file ids %s: %s",
            file_ids,
            e,
            exc_info=True,
        )
        raise
    finally:
        merger.close()
