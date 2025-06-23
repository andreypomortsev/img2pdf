import os


class Settings:
    PROJECT_NAME: str = "Image to PDF Converter"
    PROJECT_VERSION: str = "1.0.0"

    TESTING: bool = os.getenv("TESTING", "False").lower() in ("true", "1", "t")

    if TESTING:
        DATABASE_URL = "sqlite:///./test.db"
        CELERY_BROKER_URL: str = "memory://"
        CELERY_RESULT_BACKEND: str = "db+sqlite:///./test.db"
    else:
        POSTGRES_USER: str = os.getenv("POSTGRES_USER", "user")
        POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
        POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
        POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
        POSTGRES_DB: str = os.getenv("POSTGRES_DB", "mydatabase")
        DATABASE_URL = (
            f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
            f"{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
        )
        CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
        CELERY_RESULT_BACKEND: str = os.getenv(
            "CELERY_RESULT_BACKEND", "redis://redis:6379/0"
        )


settings = Settings()
