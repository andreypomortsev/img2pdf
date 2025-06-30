import os
from pathlib import Path
from typing import List, Optional


class Settings:
    PROJECT_NAME: str = "Image to PDF Converter"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"  # Base path for API v1

    # This is for detecting test mode, but the primary mechanism for setting
    # test config is conftest.py, which will monkeypatch these values.
    TESTING: bool = os.getenv("TESTING", "False").lower() in ("true", "1", "t")

    # Database settings
    # When running in Docker, use 'db' as the host (Docker service name)
    # When running locally, use 'localhost' or '127.0.0.1'
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "imgtopdf")

    # Private attribute to store the DATABASE_URL if set directly
    _database_url: str = None

    @property
    def DATABASE_URL(self) -> str:
        # If DATABASE_URL was set directly, return that
        if self._database_url is not None:
            return self._database_url

        # If DATABASE_URL is explicitly set in environment, use that
        if os.getenv("DATABASE_URL"):
            return os.getenv("DATABASE_URL")

        # If in testing mode, use SQLite in-memory database
        if self.TESTING:
            return "sqlite:///:memory:"

        # Otherwise, construct the PostgreSQL URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @DATABASE_URL.setter
    def DATABASE_URL(self, value: str) -> None:
        self._database_url = value

    # File upload settings
    UPLOAD_FOLDER: Path = Path(os.getenv("UPLOAD_FOLDER", "uploads")).resolve()

    # Production Celery settings (will be patched for tests)
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL", "redis://redis:6379/0"
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://redis:6379/0"
    )

    # Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # First superuser
    FIRST_SUPERUSER_EMAIL: Optional[str] = os.getenv("FIRST_SUPERUSER_EMAIL")
    FIRST_SUPERUSER_PASSWORD: Optional[str] = os.getenv(
        "FIRST_SUPERUSER_PASSWORD"
    )

    # Celery settings for testing (will be True only when patched by conftest.py)
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CELERY_TASK_EAGER_PROPAGATES: bool = False


settings = Settings()
