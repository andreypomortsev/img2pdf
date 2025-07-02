from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.base import Base
from app.db.init_db import init_db
from app.db.session import get_engine


def create_tables() -> None:
    """Create database tables if they don't exist."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    if not settings.TESTING:
        setup_logging()
        create_tables()
        init_db()
    yield


def create_app() -> FastAPI:
    """Factory to create FastAPI app instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description="API for converting and managing images to PDFs",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                str(origin) for origin in settings.BACKEND_CORS_ORIGINS
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Mount API routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Internal system endpoints
    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "message": "Welcome to the Image to PDF Converter API",
            "version": settings.PROJECT_VERSION,
            "docs": "/docs",
        }

    @app.get(f"{settings.API_V1_STR}/health", include_in_schema=False)
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
