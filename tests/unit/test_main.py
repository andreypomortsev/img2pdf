import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def cleanup_imports():
    """
    This fixture ensures that all 'app' modules are re-imported for each test,
    allowing environment variables to be changed and their effects tested.
    """
    # Find all modules starting with 'app.'
    app_modules = [mod for mod in sys.modules if mod.startswith("app")]
    # Delete them from sys.modules
    for module in app_modules:
        del sys.modules[module]


def test_read_root():
    """
    Tests that the root endpoint returns the correct welcome message.
    """
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {
            "message": "Welcome to the Image to PDF Converter API"
        }


@patch("app.main.create_tables")
@patch("app.main.setup_logging")
def test_lifespan_startup_production(mock_setup_logging, mock_create_tables):
    """
    Tests that create_tables and setup_logging are called on startup
    when not in TESTING mode.
    """
    with patch.dict("os.environ", {"TESTING": "False"}, clear=True):
        from app.main import app

        with TestClient(app):
            mock_setup_logging.assert_called_once()
            mock_create_tables.assert_called_once()


@patch("app.main.create_tables")
@patch("app.main.setup_logging")
def test_lifespan_startup_testing(mock_setup_logging, mock_create_tables):
    """
    Tests that create_tables and setup_logging are NOT called on startup
    when in TESTING mode.
    """
    with patch.dict("os.environ", {"TESTING": "True"}, clear=True):
        from app.main import app

        with TestClient(app):
            mock_setup_logging.assert_not_called()
            mock_create_tables.assert_not_called()
