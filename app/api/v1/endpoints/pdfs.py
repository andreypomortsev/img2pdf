import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api import deps
from app.db.session import get_db
from app.models.user import User
from app.schemas.pdf import MergePdfsRequest, MergeTaskResponse
from app.services.pdf_service import pdf_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/merge/",
    response_model=MergeTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Accepted - PDF merge task started"},
        400: {
            "description": "Bad Request - Invalid file IDs or other request error"
        },
        401: {
            "description": "Unauthorized - Invalid authentication credentials"
        },
        403: {
            "description": "Forbidden - Not authorized to access one or more files"
        },
        404: {"description": "Not Found - One or more files not found"},
    },
)
def merge_pdfs_endpoint(
    request: MergePdfsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Merge multiple PDF files into a single file.

    This endpoint allows users to merge multiple PDF files they own into a single PDF.
    Users must have read access to all specified files.
    """
    # Delegate the request handling to the PDF service
    return pdf_service.merge_pdfs_endpoint(
        db=db, request=request, current_user=current_user
    )
