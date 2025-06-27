from celery import Celery
from celery.signals import setup_logging

from app.core.config import settings


def create_celery_app() -> Celery:
    """
    Create and configure a new Celery application instance.

    Returns:
        Celery: Configured Celery application instance
    """
    app = Celery(
        "worker",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["app.tasks"],
    )

    # Configure Celery using settings
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
    )

    # Configure logging
    @setup_logging.connect
    def setup_celery_logging(**kwargs):
        from logging.config import dictConfig

        from app.core.logging import get_logging_config

        dictConfig(get_logging_config())

    return app


# Create a single Celery app instance to be used throughout the application
celery_app = create_celery_app()
