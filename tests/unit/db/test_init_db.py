import pytest
from unittest.mock import MagicMock, patch, ANY
from sqlalchemy.orm import Session

from app.db.init_db import init_db
from app.core.config import settings
from app.schemas.token import UserCreate

# Fixture for database session
@pytest.fixture
def db_session():
    """Fixture that provides a mock database session."""
    session = MagicMock(spec=Session)
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session


def test_init_db_skips_in_testing(monkeypatch, caplog):
    """Test that init_db skips user creation when in testing mode."""
    # Save original value
    original_testing = settings.TESTING
    original_email = settings.FIRST_SUPERUSER_EMAIL
    
    try:
        # Set testing mode and test email
        settings.TESTING = True
        settings.FIRST_SUPERUSER_EMAIL = "test@example.com"
        
        # Mock the database operations
        with patch('app.db.init_db.get_engine') as mock_engine, \
             patch('app.db.init_db.Base.metadata.create_all') as mock_create_all, \
             patch('app.db.init_db.Session') as mock_session, \
             patch('app.db.init_db.crud') as mock_crud:
            
            # Configure mocks
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            
            # Call the function
            init_db()
            
            # Assert database operations were called (tables are still created in testing)
            mock_engine.assert_called_once()
            mock_create_all.assert_called_once()
            
            # But no user operations should be performed
            mock_crud.get_user_by_email.assert_not_called()
            mock_crud.create_user.assert_not_called()
            
    finally:
        # Restore original values
        settings.TESTING = original_testing
        settings.FIRST_SUPERUSER_EMAIL = original_email


def test_init_db_creates_superuser(monkeypatch, db_session):
    """Test that init_db creates a superuser when one doesn't exist."""
    # Mock settings
    monkeypatch.setattr(settings, "TESTING", False)
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_EMAIL", "test@example.com")
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_PASSWORD", "testpass123")
    
    # Mock the database operations
    with patch('app.db.init_db.get_engine') as mock_engine, \
         patch('app.db.init_db.Base.metadata.create_all') as mock_create_all, \
         patch('app.db.init_db.Session') as mock_session, \
         patch('app.db.init_db.crud') as mock_crud:
        
        # Configure mocks
        mock_session.return_value = db_session
        mock_crud.get_user_by_email.return_value = None
        
        # Mock the user creation
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.is_superuser = True
        mock_crud.create_user.return_value = mock_user
        
        # Call the function
        init_db()
        
        # Assert database operations were called
        mock_engine.assert_called_once()
        mock_create_all.assert_called_once()
        
        # Assert user creation was attempted
        mock_crud.get_user_by_email.assert_called_once_with(
            db_session, email="test@example.com"
        )
        mock_crud.create_user.assert_called_once()
        
        # Get the user_create object passed to create_user
        user_create = mock_crud.create_user.call_args[1]['user']
        assert isinstance(user_create, UserCreate)
        assert user_create.email == "test@example.com"
        assert user_create.username == "test"
        assert user_create.password == "testpass123"
        assert user_create.is_superuser is True


def test_init_db_updates_existing_user(monkeypatch, db_session):
    """Test that init_db updates an existing user to superuser if needed."""
    # Mock settings
    monkeypatch.setattr(settings, "TESTING", False)
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_EMAIL", "existing@example.com")
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_PASSWORD", "testpass123")
    
    # Mock the database operations
    with patch('app.db.init_db.get_engine') as mock_engine, \
         patch('app.db.init_db.Base.metadata.create_all') as mock_create_all, \
         patch('app.db.init_db.Session') as mock_session, \
         patch('app.db.init_db.crud') as mock_crud:
        
        # Configure mocks
        mock_session.return_value = db_session
        
        # Mock an existing user who is not a superuser
        mock_user = MagicMock()
        mock_user.email = "existing@example.com"
        mock_user.is_superuser = False
        mock_crud.get_user_by_email.return_value = mock_user
        
        # Call the function
        init_db()
        
        # Assert database operations were called
        mock_engine.assert_called_once()
        mock_create_all.assert_called_once()
        
        # Assert user lookup was performed
        mock_crud.get_user_by_email.assert_called_once_with(
            db_session, email="existing@example.com"
        )
        
        # Assert user was updated to superuser
        assert mock_user.is_superuser is True
        db_session.add.assert_called_once_with(mock_user)
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once_with(mock_user)


def test_init_db_handles_exception(monkeypatch, caplog, db_session):
    """Test that init_db handles exceptions gracefully."""
    # Save original values
    original_testing = settings.TESTING
    original_email = settings.FIRST_SUPERUSER_EMAIL
    original_password = settings.FIRST_SUPERUSER_PASSWORD
    
    # Set up logging capture
    caplog.set_level("ERROR")
    
    try:
        # Mock settings
        settings.TESTING = False
        settings.FIRST_SUPERUSER_EMAIL = "error@example.com"
        settings.FIRST_SUPERUSER_PASSWORD = "testpass123"
        
        # Mock the database operations to raise an exception
        with patch('app.db.init_db.get_engine') as mock_engine, \
             patch('app.db.init_db.Base.metadata.create_all') as mock_create_all, \
             patch('app.db.init_db.Session') as mock_session, \
             patch('app.db.init_db.crud') as mock_crud, \
             patch('app.db.init_db.print') as mock_print:
            
            # Configure mocks
            mock_session.return_value = db_session
            mock_crud.get_user_by_email.side_effect = Exception("Test error")
            
            # Call the function
            init_db()
            
            # Assert database operations were called
            mock_engine.assert_called_once()
            mock_create_all.assert_called_once()
            
            # Assert error was printed (since we're mocking print)
            mock_print.assert_called_once()
            assert "Error creating initial superuser" in mock_print.call_args[0][0]
            
    finally:
        # Restore original values
        settings.TESTING = original_testing
        settings.FIRST_SUPERUSER_EMAIL = original_email
        settings.FIRST_SUPERUSER_PASSWORD = original_password