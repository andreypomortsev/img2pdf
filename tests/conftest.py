"""Pytest configuration and fixtures for testing."""
import os
import tempfile
from pathlib import Path
from typing import Generator, Any

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import User

# Import models to ensure they are registered with SQLAlchemy
from app.models.file import File  # noqa: F401

# Enable foreign key constraints for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.TESTING and "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.fixture(scope="session")
def monkeypatch_session() -> Generator[MonkeyPatch, None, None]:
    """A session-scoped monkeypatch to prevent scope mismatch errors."""
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session", autouse=True)
def apply_test_settings(monkeypatch_session: MonkeyPatch) -> None:
    """
    Apply test settings for the entire test session.
    
    This fixture ensures that all parts of the application use a test configuration
    by monkeypatching the settings object before any other code imports it.
    """
    # Create a temporary directory for test files
    temp_dir = tempfile.mkdtemp()
    
    # Set test settings
    test_settings = {
        "TESTING": True,
        "DATABASE_URL": "sqlite:///:memory:",
        "UPLOAD_FOLDER": os.path.join(temp_dir, "uploads"),
        "CELERY_BROKER_URL": "memory://",
        "CELERY_RESULT_BACKEND": "rpc://",
        "CELERY_TASK_ALWAYS_EAGER": True,
        "CELERY_TASK_EAGER_PROPAGATES": True,
        "SECRET_KEY": "test-secret-key",
        "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
    }

    # Apply settings
    for key, value in test_settings.items():
        monkeypatch_session.setattr(settings, key, value)

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)

    # Import Celery app after settings are applied
    from app.worker import celery_app

    # Force update Celery configuration
    celery_app.conf.update(
        broker_url=settings.CELERY_BROKER_URL,
        result_backend=settings.CELERY_RESULT_BACKEND,
        task_always_eager=True,
        task_eager_propagates=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_ignore_result=True,
    )

    # Make sure the Celery app is using the test configuration
    assert (
        celery_app.conf.task_always_eager is True
    ), "Celery is not running in eager mode"

    # Re-import the tasks module to ensure they use the updated Celery app
    import importlib

    from app import tasks

    importlib.reload(tasks)

    # Also update the celery_app in the tasks module
    setattr(tasks, "celery_app", celery_app)


@pytest.fixture(scope="session")
def engine() -> Engine:
    """
    Create a new in-memory SQLite engine for the entire test session.
    
    The `connect_args` and `poolclass` are crucial for SQLite in-memory usage.
    It relies on `apply_test_settings` having already run due to autouse=True.
    """
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=bool(os.getenv("SQL_ECHO", False)),
    )
    return engine


@pytest.fixture(scope="session", autouse=True)
def setup_tables(engine):
    """
    Creates the database tables once per session before any tests run,
    and drops them after all tests have completed.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """
    Provide a transactional scope for integration tests.
    
    A transaction is started before the test and rolled back after,
    ensuring a clean slate for each test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = session_factory()

    # Override the get_db dependency to use our test session
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield session
        finally:
            session.close()

    yield session

    # Clean up
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Create a FastAPI TestClient for testing API endpoints.
    
    This fixture overrides the database dependency to use the test session.
    """
    app = create_app()
    
    # Override the get_db dependency
    app.dependency_overrides[get_db] = lambda: db_session
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user with hashed password."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_superuser(db_session: Session) -> User:
    """Create a test superuser."""
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def authorized_client(client: TestClient, test_user: User) -> TestClient:
    """Return an authorized client with a valid JWT token."""
    from app.core.security import create_access_token
    
    access_token = create_access_token(subject=test_user.email)
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


@pytest.fixture
def test_file(db_session: Session, test_user: User) -> File:
    """Create a test file in the database."""
    file = File(
        filename="test.txt",
        filepath="/uploads/test.txt",
        size=1024,
        content_type="text/plain",
        owner_id=test_user.id,
    )
    db_session.add(file)
    db_session.commit()
    db_session.refresh(file)
    return file


@pytest.fixture(scope="function")
def celery_db_session(engine, monkeypatch):
    """
    Provides a database session specifically for Celery tasks during testing.
    This ensures that Celery tasks use the same test database as the main test session.

    This fixture:
    1. Creates all database tables
    2. Creates a new session bound to the test engine
    3. Mocks the database session in the tasks module
    4. Cleans up after the test
    """
    # Create all tables in the test database
    from app.db.base import Base

    Base.metadata.create_all(bind=engine)

    # Create a new session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Create a function that will return our test session
    def get_test_db():
        try:
            yield db
        finally:
            pass  # Don't close the session here, let the fixture handle it

    # Apply the mock to the tasks module
    monkeypatch.setattr("app.tasks.get_db", get_test_db)

    # Also patch the get_db dependency in the main app
    from app.api.deps import get_db as original_get_db
    from app.main import app

    # Store the original function so we can restore it later
    original_get_db_fn = getattr(original_get_db, "_original_get_db", original_get_db)

    # Create a wrapper that will use our test session
    def get_db_override():
        try:
            yield db
        finally:
            pass  # Don't close the session here, let the fixture handle it

    # Mark the original function so we can find it later
    get_db_override._original_get_db = original_get_db_fn

    # Apply the override
    app.dependency_overrides[original_get_db_fn] = get_db_override

    try:
        yield db
    finally:
        # Clean up
        db.rollback()
        db.close()

        # Remove the override
        if original_get_db_fn in app.dependency_overrides:
            del app.dependency_overrides[original_get_db_fn]


@pytest.fixture(scope="function")
def client(db_session):
    """
    Provides a FastAPI TestClient for integration tests.
    It overrides the `get_db` dependency to use the transactional `db_session`
    fixture, ensuring that API endpoints interact with the test database.

    Note: We import create_app here to ensure test settings are applied before
    the FastAPI app is created.
    """
    # Import here to ensure test settings are applied first
    from app.db.session import get_db
    from app.main import create_app

    # Create the FastAPI app
    app = create_app()

    # Override the database dependency
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create and return the test client
    with TestClient(app) as c:
        yield c
