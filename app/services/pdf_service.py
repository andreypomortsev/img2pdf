"""
PDF processing service.

This module contains the business logic for PDF operations,
separated from the Celery task definitions.
"""

import logging
import os
from typing import List

import img2pdf
from pypdf import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file import File
from app.schemas.file import FileCreate

logger = logging.getLogger(__name__)

TEMP_DIR = settings.UPLOAD_FOLDER / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def convert_image_to_pdf(db: Session, file_id: int, owner_id: int) -> File:
    """
    Convert an image file to PDF.

    Args:
        db: Database session
        file_id: ID of the image file to convert
        owner_id: ID of the user who owns the file

    Returns:
        File: The newly created PDF file record

    Raises:
        ValueError: If the file is not found or not an image
    """
    logger.info("Converting image to PDF for file id %s", file_id)

    image_file = db.query(File).filter(File.id == file_id).first()
    if not image_file:
        raise ValueError(f"File with id {file_id} not found.")

    # Read image and convert to PDF
    try:
        with open(image_file.filepath, "rb") as f:
            try:
                pdf_bytes = img2pdf.convert([f.read()])
            except img2pdf.ImageOpenError as e:
                raise ValueError(f"Failed to convert image to PDF: {str(e)}") from e
            except Exception as e:
                logger.error(f"Unexpected error during PDF conversion: {str(e)}")
                raise ValueError(f"Failed to convert image to PDF: {str(e)}") from e

        # Create output filename and path
        pdf_filename = f"{os.path.splitext(image_file.filename)[0]}.pdf"
        output_path = settings.UPLOAD_FOLDER / pdf_filename

        # Save PDF to disk
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
    except OSError as e:
        logger.error(f"File operation error: {str(e)}")
        raise ValueError(f"Failed to process file: {str(e)}") from e

    # Create file record
    file_data = FileCreate(
        filename=pdf_filename,
        filepath=str(output_path),
        content_type="application/pdf",
        owner_id=owner_id,
    )

    db_file = File(**file_data.model_dump())
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    return db_file


def merge_pdfs(
    db: Session, file_ids: List[int], output_filename: str, owner_id: int
) -> File:
    """
    Merge multiple PDF files into a single PDF.

    Args:
        db: Database session
        file_ids: List of file IDs to merge
        output_filename: Name of the output PDF file
        owner_id: ID of the user who owns the files

    Returns:
        File: The newly created merged PDF file record

    Raises:
        ValueError: If no files provided or any file is not found or not a PDF
    """
    logger.info("Merging PDFs for file ids: %s", file_ids)

    # Check for empty input
    if not file_ids:
        raise ValueError("No PDF files to merge")

    # Get all input files
    pdf_files = db.query(File).filter(File.id.in_(file_ids)).all()
    if len(pdf_files) != len(file_ids):
        found_ids = {f.id for f in pdf_files}
        missing_ids = set(file_ids) - found_ids
        raise ValueError(f"Files with ids {missing_ids} not found.")

    # Ensure output directory exists
    output_path = TEMP_DIR / output_filename
    logger.info("Output path: %s", output_path)
    logger.info("Output directory exists: %s", output_path.parent.exists())

    # Create parent directories if they don't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory created/exists: %s", output_path.parent.exists())

    # Verify input files exist and are readable
    for pdf_file in pdf_files:
        logger.info(
            "Input file: %s, exists: %s, readable: %s",
            pdf_file.filepath,
            os.path.exists(pdf_file.filepath),
            os.access(pdf_file.filepath, os.R_OK),
        )

    # Merge PDFs
    writer = PdfWriter()
    try:
        for pdf_file in pdf_files:
            try:
                logger.info("Reading PDF: %s", pdf_file.filepath)
                reader = PdfReader(pdf_file.filepath)
                logger.info(
                    "Adding %d pages from %s", len(reader.pages), pdf_file.filename
                )
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as e:
                logger.error(
                    "Error reading PDF %s: %s", pdf_file.filepath, str(e), exc_info=True
                )
                raise ValueError(f"Error reading PDF {pdf_file.filename}: {str(e)}")

        # Write merged PDF to disk
        logger.info("Writing merged PDF to: %s", output_path)
        with open(output_path, "wb") as out_file:
            writer.write(out_file)

        logger.info(
            "Merged PDF written successfully. File exists: %s, size: %d bytes",
            output_path.exists(),
            output_path.stat().st_size if output_path.exists() else 0,
        )

        # Create file record
        file_data = FileCreate(
            filename=output_filename,
            filepath=str(output_path),
            content_type="application/pdf",
            owner_id=owner_id,
        )

        db_file = File(**file_data.model_dump())
        db.add(db_file)
        db.commit()
        db.refresh(db_file)

        return db_file

    finally:
        writer.close()
