"""Interface for task service to avoid circular imports."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from sqlalchemy.orm import Session


class TaskServiceInterface(ABC):
    """Interface for task service operations."""

    @abstractmethod
    def convert_image_to_pdf(
        self, db: Session, file_id: int, owner_id: int
    ) -> Dict[str, Any]:
        """Convert an image to PDF."""
        pass

    @abstractmethod
    def merge_pdfs(
        self,
        db: Session,
        file_ids: List[int],
        output_filename: str,
        owner_id: int,
    ) -> Dict[str, Any]:
        """Merge multiple PDFs into one."""
        pass
