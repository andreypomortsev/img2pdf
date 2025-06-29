from fastapi import APIRouter

from app.api.v1.endpoints import auth, files, pdfs

# Create the API router without a prefix since it will be added in main.py
api_router = APIRouter()

# Include routers with their respective prefixes
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(pdfs.router, prefix="/pdfs", tags=["pdfs"])
