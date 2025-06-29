from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.file import File as FileModel
from app.schemas.file import FileCreate, FileUpdate


class CRUDFile(CRUDBase[FileModel, FileCreate, FileUpdate]):
    """CRUD operations for File model"""

    def get_by_id(self, db: Session, *, id: int) -> Optional[FileModel]:
        """Get a file by ID"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> list[FileModel]:
        """Get multiple files by owner ID"""
        return (
            db.query(self.model)
            .filter(self.model.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .all()
        )


# Create a singleton instance
file = CRUDFile(FileModel)
