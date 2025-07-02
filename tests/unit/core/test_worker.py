"""Tests for the Celery worker configuration."""

from unittest.mock import patch

from celery import Celery

from app.core.config import settings
from app.worker import celery_app as celery_app_instance
from app.worker import create_celery_app


def test_create_celery_app():
    """Test creating and configuring a Celery app instance."""
    app = create_celery_app()

    assert isinstance(app, Celery)
    assert app.main == "worker"
    assert app.conf.broker_url == settings.CELERY_BROKER_URL
    assert app.conf.result_backend == settings.CELERY_RESULT_BACKEND
    assert app.conf.task_serializer == "json"
    assert app.conf.accept_content == ["json"]
    assert app.conf.result_serializer == "json"
    assert app.conf.timezone == "UTC"
    assert app.conf.enable_utc is True
    assert app.conf.task_track_started is True
    assert app.conf.task_time_limit == 30 * 60  # 30 minutes
    assert app.conf.task_soft_time_limit == 25 * 60  # 25 minutes


def test_celery_app_instance():
    """Test that the celery_app instance is properly configured."""
    assert celery_app_instance is not None
    assert isinstance(celery_app_instance, Celery)
    assert "app.tasks" in celery_app_instance.conf.include


def test_worker_import():
    """Test that the worker module can be imported
    and has expected attributes."""
    from app.worker import (  # pylint: disable=import-outside-toplevel
        celery_app, create_celery_app)

    assert callable(create_celery_app)
    assert hasattr(celery_app, "conf")


def test_worker_logging_config():
    """Test that the Celery app is properly configured with logging."""
    app = create_celery_app()
    assert app is not None


@patch("app.worker.celery_setup_logging.connect")
@patch("app.worker.setup_app_logging")
def test_configure_celery_logging(mock_setup_logging, mock_connect):
    """Test that the Celery logging configuration works correctly."""
    from app.worker import (  # pylint: disable=import-outside-toplevel
        configure_celery_logging, create_celery_app)

    configure_celery_logging()
    mock_setup_logging.assert_called_once()

    with patch("app.worker.celery_setup_logging.connect") as mock_connect_fn:
        create_celery_app()

        mock_connect_fn.assert_called_once()

        signal_handler = mock_connect_fn.call_args[0][0]

        with patch("app.worker.setup_app_logging") as mock_logging:
            signal_handler()
            mock_logging.assert_called_once()
