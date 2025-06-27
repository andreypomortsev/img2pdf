from fastapi import APIRouter

from app.api.v1.endpoints import auth, files, pdfs
from app.core.config import settings

api_router = APIRouter(prefix=settings.API_V1_STR)

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(pdfs.router, prefix="/pdfs", tags=["pdfs"])
