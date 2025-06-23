import os
import sys
from unittest.mock import patch

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
        assert settings.POSTGRES_USER == "user"
        assert settings.POSTGRES_PASSWORD == "password"
        assert settings.POSTGRES_SERVER == "db"
        assert settings.POSTGRES_PORT == "5432"
        assert settings.POSTGRES_DB == "mydatabase"
        assert (
            str(settings.DATABASE_URL)
            == "postgresql://user:password@db:5432/mydatabase"
        )
        assert settings.CELERY_BROKER_URL == "redis://redis:6379/0"
        assert settings.CELERY_RESULT_BACKEND == "redis://redis:6379/0"


def test_testing_settings():
    """Tests that testing settings are loaded correctly when TESTING=True."""
    with patch.dict(os.environ, {"TESTING": "True"}):
        from app.core.config import Settings

        settings = Settings()
        assert settings.TESTING is True
        assert str(settings.DATABASE_URL) == "sqlite:///./test.db"
        assert settings.CELERY_BROKER_URL == "memory://"
        assert settings.CELERY_RESULT_BACKEND == "db+sqlite:///./test.db"


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
