import os
import sys
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def cleanup_imports():
    """
    This fixture ensures that app.core.config is re-imported for each test,
    allowing environment variables to be changed and their effects tested.
    """
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]


def test_default_production_settings():
    """Tests the default values for production settings when no env vars are set."""
    with patch.dict(os.environ, {"TESTING": "False"}, clear=True):
        from app.core.config import Settings

        settings = Settings()
        assert settings.TESTING is False
        assert settings.POSTGRES_USER == "postgres"
        assert settings.POSTGRES_PASSWORD == "postgres"
        assert settings.POSTGRES_SERVER == "localhost"
        assert settings.POSTGRES_PORT == "5432"
        assert settings.POSTGRES_DB == "imgtopdf"
        assert (
            str(settings.DATABASE_URL)
            == "postgresql://postgres:postgres@localhost:5432/imgtopdf"
        )
        # These values are not set by default in the Settings class
        # and will be None unless set in the environment
        assert settings.CELERY_BROKER_URL == "redis://redis:6379/0"
        assert settings.CELERY_RESULT_BACKEND == "redis://redis:6379/0"


def test_testing_settings(monkeypatch):
    """Tests that testing settings are loaded correctly when TESTING=True."""
    # Clear any existing settings module import to ensure a fresh import
    import sys

    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]

    # Set up the test environment
    monkeypatch.setenv("TESTING", "True")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("CELERY_BROKER_URL", "memory://")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "rpc://")

    # Now import the settings
    from app.core.config import Settings, settings

    # Create a new Settings instance
    test_settings = Settings()

    # Verify the settings
    assert test_settings.TESTING is True
    assert str(test_settings.DATABASE_URL) == "sqlite:///:memory:"
    assert test_settings.CELERY_BROKER_URL == "memory://"
    assert test_settings.CELERY_RESULT_BACKEND == "rpc://"


@patch.dict(
    os.environ,
    {
        "TESTING": "False",
        "POSTGRES_USER": "prod_user",
        "POSTGRES_PASSWORD": "prod_password",
        "POSTGRES_SERVER": "prod_db",
        "POSTGRES_PORT": "5433",
        "POSTGRES_DB": "prod_app",
        "CELERY_BROKER_URL": "redis://prod_redis:6379/1",
        "CELERY_RESULT_BACKEND": "redis://prod_redis:6379/2",
    },
)
def test_production_settings_from_env():
    """Tests that production settings are loaded correctly from environment variables."""
    from app.core.config import Settings

    settings = Settings()
    assert settings.TESTING is False
    assert settings.POSTGRES_USER == "prod_user"
    assert settings.POSTGRES_PASSWORD == "prod_password"
    assert (
        str(settings.DATABASE_URL)
        == "postgresql://prod_user:prod_password@prod_db:5433/prod_app"
    )
    assert settings.CELERY_BROKER_URL == "redis://prod_redis:6379/1"
    assert settings.CELERY_RESULT_BACKEND == "redis://prod_redis:6379/2"


def test_database_url_setter():
    """Test that the DATABASE_URL setter works correctly."""
    from app.core.config import Settings
    
    settings = Settings()
    test_url = "postgresql://user:pass@server:5432/db"
    
    # Set the DATABASE_URL
    settings.DATABASE_URL = test_url
    
    # Verify it was set correctly
    assert settings.DATABASE_URL == test_url
    
    # Verify it overrides the constructed URL
    assert settings.DATABASE_URL != "postgresql://postgres:postgres@localhost:5432/imgtopdf"


def test_upload_folder_default():
    """Test the default UPLOAD_FOLDER value."""
    from app.core.config import Settings
    
    settings = Settings()
    assert settings.UPLOAD_FOLDER == "uploads"


def test_upload_folder_override():
    """Test that UPLOAD_FOLDER can be overridden by environment variable."""
    with patch.dict(os.environ, {"UPLOAD_FOLDER": "/custom/uploads"}):
        from app.core.config import Settings
        settings = Settings()
        assert settings.UPLOAD_FOLDER == "/custom/uploads"


def test_security_defaults():
    """Test default security-related settings."""
    from app.core.config import Settings
    
    settings = Settings()
    assert settings.SECRET_KEY is not None
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60 * 24 * 8  # 8 days


def test_cors_defaults():
    """Test default CORS settings."""
    from app.core.config import Settings
    
    settings = Settings()
    assert isinstance(settings.BACKEND_CORS_ORIGINS, list)
    assert "http://localhost" in settings.BACKEND_CORS_ORIGINS
    assert "http://localhost:3000" in settings.BACKEND_CORS_ORIGINS
    assert "http://localhost:8000" in settings.BACKEND_CORS_ORIGINS


def test_superuser_env_vars():
    """Test that superuser environment variables are loaded correctly."""
    with patch.dict(os.environ, {
        "FIRST_SUPERUSER_EMAIL": "admin@example.com",
        "FIRST_SUPERUSER_PASSWORD": "admin123"
    }):
        from app.core.config import Settings
        settings = Settings()
        assert settings.FIRST_SUPERUSER_EMAIL == "admin@example.com"
        assert settings.FIRST_SUPERUSER_PASSWORD == "admin123"


def test_celery_eager_settings():
    """Test Celery eager execution settings."""
    from app.core.config import Settings
    
    settings = Settings()
    assert settings.CELERY_TASK_ALWAYS_EAGER is False
    assert settings.CELERY_TASK_EAGER_PROPAGATES is False


def test_database_url_priority():
    """Test that DATABASE_URL takes precedence over individual DB settings."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://user:pass@server:5432/db",
        "POSTGRES_USER": "ignored_user",
        "POSTGRES_PASSWORD": "ignored_pass",
        "POSTGRES_SERVER": "ignored_server",
        "POSTGRES_PORT": "1234",
        "POSTGRES_DB": "ignored_db"
    }):
        from app.core.config import Settings
        settings = Settings()
        assert settings.DATABASE_URL == "postgresql://user:pass@server:5432/db"
        # Individual settings should be ignored when DATABASE_URL is set
        assert settings.POSTGRES_USER == "ignored_user"  # These are still set but not used
        assert settings.POSTGRES_PASSWORD == "ignored_pass"
        assert settings.POSTGRES_SERVER == "ignored_server"
        assert settings.POSTGRES_PORT == "1234"
        assert settings.POSTGRES_DB == "ignored_db"


def test_testing_mode_behavior():
    """Test that TESTING mode affects database URL and other settings."""
    with patch.dict(os.environ, {"TESTING": "True"}):
        from app.core.config import Settings
        settings = Settings()
        assert settings.TESTING is True
        assert settings.DATABASE_URL == "sqlite:///:memory:"
