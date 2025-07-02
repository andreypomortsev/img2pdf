"""Celery worker configuration and setup.

This module configures and initializes the Celery application used for
asynchronous task processing in the application.
"""

from typing import Any

from celery import Celery
from celery.signals import setup_logging as celery_setup_logging

from app.core.config import settings
from app.core.logging_config import setup_logging as setup_app_logging


def configure_celery_logging(**kwargs: Any) -> None:
    """Configure Celery logging.

    This function is connected to the Celery setup_logging signal to configure
    logging when the Celery worker starts.

    Args:
        **kwargs: Additional keyword arguments (provided by Celery signal)
    """
    del kwargs  # Unused
    setup_app_logging()


def create_celery_app() -> Celery:
    """Create and configure a new Celery application instance.

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
    celery_setup_logging.connect(configure_celery_logging, weak=False)

    return app


# Create a single Celery app instance to be used throughout the application
celery_app = create_celery_app()
