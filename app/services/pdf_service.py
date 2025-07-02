"""
PDF processing service.

This module contains the business logic for PDF operations,
separated from the Celery task definitions.
"""

import logging
import os
from typing import List

import img2pdf
from fastapi import HTTPException, status
from pypdf import PdfWriter
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.interfaces.task_service_interface import TaskServiceInterface
from app.models.file import File
from app.models.file import File as FileModel
from app.models.user import User
from app.schemas.file import FileCreate
from app.schemas.pdf import MergePdfsRequest, MergeTaskResponse

logger = logging.getLogger(__name__)


class PDFService:
    """Service for handling PDF-related operations."""

    def __init__(self, task_service: TaskServiceInterface):
        """Initialize PDF service with task service dependency."""
        self.task_service = task_service
        self.temp_dir = settings.UPLOAD_FOLDER / "temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    def convert_image_to_pdf(
        self, db: Session, file_id: int, owner_id: int
    ) -> File:
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
                    raise ValueError(
                        f"Failed to convert image to PDF: {str(e)}"
                    ) from e
                except Exception as e:
                    logger.error(
                        f"Unexpected error during PDF conversion: {str(e)}"
                    )
                    raise ValueError(
                        f"Failed to convert image to PDF: {str(e)}"
                    ) from e

            # Create output filename and path
            pdf_filename = f"{os.path.splitext(image_file.filename)[0]}.pdf"
            output_path = settings.UPLOAD_FOLDER / str(owner_id) / pdf_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save PDF to disk
            with open(output_path, "wb") as f_out:
                f_out.write(pdf_bytes)

            # Create file record
            file_data = FileCreate(
                filename=pdf_filename,
                filepath=str(output_path),
                content_type="application/pdf",
                owner_id=owner_id,  # Set the owner_id in the file data
            )

            db_file = crud.file.create(db=db, obj_in=file_data)
            db.commit()
            db.refresh(db_file)

            return db_file

        except OSError as e:
            logger.error(f"File operation error: {str(e)}")
            raise ValueError(f"Failed to process file: {str(e)}") from e

    def merge_pdfs(
        self,
        db: Session,
        file_ids: List[int],
        output_filename: str,
        owner_id: int,
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
        if not file_ids:
            raise ValueError("No files provided to merge.")

        logger.info(
            "Merging PDFs with ids %s into %s for user %s",
            file_ids,
            output_filename,
            owner_id,
        )

        # Ensure output filename ends with .pdf
        if not output_filename.lower().endswith(".pdf"):
            output_filename += ".pdf"

        # Create output directory if it doesn't exist
        output_dir = settings.UPLOAD_FOLDER / str(owner_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename

        # Check for existing file with same name and append number if needed
        counter = 1
        original_name = output_path.stem
        while output_path.exists():
            output_path = output_dir / f"{original_name}_{counter}.pdf"
            counter += 1

        # Get all files and verify they exist and are PDFs
        files = []
        for file_id in file_ids:
            file = crud.file.get(db, id=file_id)
            if not file:
                raise ValueError(f"File with ID {file_id} not found")
            if not file.filepath.lower().endswith(".pdf"):
                raise ValueError(f"File with ID {file_id} is not a PDF")
            if file.owner_id != owner_id:
                raise ValueError(
                    f"Not authorized to access file with ID {file_id}"
                )
            files.append(file)

        # Merge PDFs
        merger = PdfWriter()
        try:
            for file in files:
                try:
                    merger.append(file.filepath)
                except Exception as e:
                    raise ValueError(
                        f"Error reading file {file.id}: {str(e)}"
                    ) from e

            # Write merged PDF to disk
            with open(output_path, "wb") as output_file:
                merger.write(output_file)

            # Create file record
            # Create the file record directly using FileModel
            db_file = FileModel(
                filename=output_path.name,
                filepath=str(output_path),
                content_type="application/pdf",
                owner_id=owner_id,
            )
            db.add(db_file)
            db.commit()
            db.refresh(db_file)

            return db_file

        except Exception as e:
            # Clean up the output file if it was created
            if output_path.exists():
                try:
                    output_path.unlink()
                except OSError:
                    logger.warning(
                        f"Failed to clean up output file: {output_path}"
                    )
            raise ValueError(f"Failed to merge PDFs: {str(e)}") from e

        finally:
            # Ensure the merger is always closed
            try:
                merger.close()
            except Exception as e:
                logger.warning(f"Error closing PDF merger: {str(e)}")

    def merge_pdfs_endpoint(
        self, db: Session, request: MergePdfsRequest, current_user: User
    ) -> MergeTaskResponse:
        """
        Handle the PDF merge HTTP endpoint.

        Args:
            db: Database session
            request: The merge PDFs request containing file IDs and output filename
            current_user: The currently authenticated user

        Returns:
            MergeTaskResponse: The response containing the task ID

        Raises:
            HTTPException: If there's an error processing the request
        """
        try:
            # Log the merge request
            logger.info(
                "User %s requested to merge files %s into %s",
                current_user.id,
                request.file_ids,
                request.output_filename,
            )

            # Call the merge_pdfs method to perform the actual merge
            merged_file = self.merge_pdfs(
                db=db,
                file_ids=request.file_ids,
                output_filename=request.output_filename,
                owner_id=current_user.id,
            )

            # Delegate task creation to the task service
            return task_service.create_merge_task(db, request, current_user)

        except ValueError as e:
            # Handle validation errors
            logger.warning(
                "Validation error in merge_pdfs_endpoint for user %s: %s",
                current_user.id,
                str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )
        except Exception as e:
            # Handle unexpected errors
            logger.error(
                "Error in merge_pdfs_endpoint for user %s: %s",
                current_user.id,
                str(e),
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while processing your request",
            )


# Note: Instantiation is now handled in app/services/__init__.py
