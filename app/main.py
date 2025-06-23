from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.base import Base
from app.db.session import engine


def create_tables():
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.TESTING:
        setup_logging()
        create_tables()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION, lifespan=lifespan
)


app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Welcome to the Image to PDF Converter API"}
