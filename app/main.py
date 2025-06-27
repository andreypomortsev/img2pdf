from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.base import Base
from app.db.init_db import init_db
from app.db.session import get_engine


def create_tables():
    """Create database tables if they don't exist."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    if not settings.TESTING:
        setup_logging()
        create_tables()
        # Initialize data (e.g., create first superuser)
        init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description="API for converting and managing images to PDFs",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Set up CORS
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Serve static files (if needed)
    # app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def root() -> dict[str, str]:
        """
        Root endpoint for the API.

        Returns:
            A welcome message with API information.
        """
        return {
            "message": "Welcome to the Image to PDF Converter API",
            "version": settings.PROJECT_VERSION,
            "docs": "/docs",
        }

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint for monitoring."""
        return {"status": "ok"}

    return app


app = create_app()

@app.get("/api/v1/health", status_code=200)
async def health_check() -> dict:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "ok"}
