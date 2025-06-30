import logging
import os
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import crud
from app.models.file import File as FileModel
from app.models.user import User
from app.tasks import convert_image_to_pdf, merge_pdfs
from app.worker import celery_app

logger = logging.getLogger(__name__)

TEMP_DIR = Path("tmp")


class FileService:
    def save_file(
        self, 
        db: Session, 
        file: UploadFile, 
        owner_id: int, 
        content_type: str
    ) -> FileModel:
        """Save an uploaded file and return the database record.
        
        Args:
            db: Database session
            file: Uploaded file
            owner_id: ID of the user who owns the file
            content_type: MIME type of the file
            
        Returns:
            FileModel: The created file record
            
        Raises:
            HTTPException: If there's an error saving the file
        """
        logger.info("Saving file: %s for user: %s", file.filename, owner_id)
        
        try:
            # Create a unique directory for the file
            unique_dir = TEMP_DIR / str(uuid.uuid4())
            unique_dir.mkdir(parents=True, exist_ok=True)
            filepath = unique_dir / file.filename

            # Read the file content and write it to the destination
            with open(filepath, "wb") as buffer:
                buffer.write(file.file.read())

            logger.info("File %s saved to %s", file.filename, filepath)

            db_file = FileModel(
                filename=file.filename,
                filepath=str(filepath),
                owner_id=owner_id,
                content_type=content_type
            )
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save file"
            ) from e

    def get_file_by_id(
        self, 
        db: Session, 
        file_id: int, 
        current_user: User,
        check_owner: bool = True
    ) -> FileModel:
        """Get a file by ID with optional ownership check.
        
        Args:
            db: Database session
            file_id: ID of the file to retrieve
            current_user: Currently authenticated user
            check_owner: Whether to verify the user owns the file
            
        Returns:
            FileModel: The requested file
            
        Raises:
            HTTPException: If file not found or permission denied
        """
        logger.info("Fetching file with id %s from database", file_id)
        try:
            db_file = db.query(FileModel).filter(FileModel.id == file_id).first()
            if not db_file:
                logger.warning("File with id %s not found in database", file_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found",
                )
                
            # Check ownership if required
            if check_owner and db_file.owner_id != current_user.id and not current_user.is_superuser:
                logger.warning(
                    "User %s is not authorized to access file %s",
                    current_user.id,
                    file_id
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this file",
                )
                
            logger.info("File with id %s found: %s", file_id, db_file.filename)
            return db_file
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Error fetching file %s from database: %s",
                file_id,
                e,
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve file"
            ) from e

    def create_merge_task(self, file_ids: list[int], output_filename: str):
        """Create a task to merge multiple PDFs.
        
        Args:
            file_ids: List of file IDs to merge
            output_filename: Name for the merged output file
            
        Returns:
            The Celery task
            
        Raises:
            HTTPException: If there's an error creating the task
        """
        logger.info("Creating merge task for files %s into %s", file_ids, output_filename)
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create merge task"
            ) from e
            
    def list_user_files(
        self, 
        db: Session, 
        current_user: User, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[FileModel]:
        """List files for the current user.
        
        Args:
            db: Database session
            current_user: Currently authenticated user
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of FileModel instances
        """
        try:
            if current_user.is_superuser:
                return db.query(FileModel).offset(skip).limit(limit).all()
            return (
                db.query(FileModel)
                .filter(FileModel.owner_id == current_user.id)
                .offset(skip)
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error("Error listing files: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list files"
            ) from e
            
    def get_task_status(
        self, 
        task_id: str, 
        db: Session, 
        current_user: User
    ) -> dict:
        """Get the status of a Celery task.
        
        Args:
            task_id: ID of the Celery task
            db: Database session
            current_user: Currently authenticated user
            
        Returns:
            dict: Task status and result if available
            
        Raises:
            HTTPException: If task not found or permission denied
        """
        task_result = AsyncResult(task_id, app=celery_app)

        # If task is ready, verify the user has access to the result
        if task_result.ready() and task_result.result and isinstance(task_result.result, dict):
            file_id = task_result.result.get("file_id")
            if file_id:
                # This will raise appropriate HTTP exceptions if access is denied
                self.get_file_by_id(db, file_id, current_user)
                
        logger.info("Task %s status: %s", task_id, task_result.status)
        return {
            "task_id": task_id,
            "status": task_result.status,
            "result": task_result.result if task_result.ready() else None,
        }
        
    def start_image_conversion(
        self, 
        db: Session, 
        file: UploadFile, 
        current_user: User
    ) -> dict:
        """Start image to PDF conversion process.
        
        Args:
            db: Database session
            file: Uploaded image file
            current_user: Currently authenticated user
            
        Returns:
            dict: Contains task_id and file_id
            
        Raises:
            HTTPException: If file type is unsupported or processing fails
        """
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file.content_type}",
            )
            
        try:
            # Save the file with owner information
            db_file = self.save_file(
                db=db, 
                file=file, 
                owner_id=current_user.id, 
                content_type=file.content_type
            )

            # Commit the session to make the file object available to the worker
            db.commit()

            # Dispatch Celery task for PDF conversion
            task = convert_image_to_pdf.delay(db_file.id)
            logger.info(
                "Created conversion task %s for file %s (user_id: %s)",
                task.id,
                file.filename,
                current_user.id,
            )
            return {"task_id": task.id, "file_id": db_file.id}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Error processing file %s: %s", 
                file.filename, 
                e, 
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process file"
            ) from e


file_service = FileService()
