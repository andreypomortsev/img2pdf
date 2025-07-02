"""Pytest configuration and fixtures for testing."""

import io
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.models.file import File
from app.models.user import User


# Enable foreign key constraints for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """Set SQLite pragmas for better transaction support."""
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


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup is handled by the OS when the directory is removed


@pytest.fixture(scope="session")
def test_image() -> bytes:
    """Generate a test image for testing file uploads and conversions."""
    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def test_pdf() -> bytes:
    """Generate a simple PDF file for testing."""
    # This is a minimal PDF file with a single blank page
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000015 00000 n \n0000000060 00000 n \n0000000116 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
    )


@pytest.fixture(scope="function")
def mock_current_user():
    """Create a mock current user for testing."""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture(scope="session")
def apply_test_settings(
    monkeypatch_session: MonkeyPatch, temp_dir: Path
) -> None:
    """
    Apply test settings for the entire test session.

    This fixture ensures that all parts of the application use a test configuration
    by monkeypatching the settings object before any other code imports it.
    """
    # Set test settings
    test_settings = {
        "TESTING": True,
        "DATABASE_URL": "sqlite:///:memory:",
        "UPLOAD_FOLDER": str(temp_dir / "uploads"),
        "CELERY_BROKER_URL": "memory://",
        "CELERY_RESULT_BACKEND": "rpc://",
        "CELERY_TASK_ALWAYS_EAGER": True,
        "CELERY_TASK_EAGER_PROPAGATES": True,
        "SECRET_KEY": "test-secret-key",
        "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
        "JWT_ALGORITHM": "HS256",
        "JWT_SECRET_KEY": "test-secret-key",
    }

    # Apply settings
    for key, value in test_settings.items():
        monkeypatch_session.setattr(settings, key, value)


@pytest.fixture(scope="session")
def engine() -> Engine:
    """
    Create a new in-memory SQLite engine for the entire test session.
    """
    # Create a new SQLAlchemy engine with SQLite-specific parameters
    engine = create_engine(
        "sqlite:///:memory:",  # Force SQLite in-memory database
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=bool(os.getenv("SQL_ECHO")),
    )

    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture(scope="session", autouse=True)
def setup_tables(engine: Engine) -> Generator[None, None, None]:
    """
    Creates the database tables once per session before any tests run,
    and drops them after all tests have completed.
    """
    print("\n=== Setting up test database ===")
    print("\n=== Creating database tables ===")

    # Drop all tables first to ensure a clean state
    Base.metadata.drop_all(bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Get the list of tables that should exist
    expected_tables = list(Base.metadata.tables.keys())
    print(f"=== Expected tables: {expected_tables} ===")

    # Verify tables were created
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n=== Created tables: {tables} ===")

    if not tables:
        print("WARNING: No tables were created!")

    # Verify all expected tables exist
    missing_tables = set(expected_tables) - set(tables)
    if missing_tables:
        raise RuntimeError(f"Missing tables in database: {missing_tables}")

    # Create a session to verify we can interact with the database
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        # Simple query to verify the database is accessible
        db.execute(text("SELECT 1"))
        print("Database connection verified!")
    except Exception as e:
        print(f"Database verification failed: {e}")
        raise
    finally:
        db.close()

    yield

    # Clean up
    print("\n=== Cleaning up test database ===")
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """
    Provide a transactional scope for integration tests.

    Creates a new database session with a savepoint, and rolls back all changes
    after the test completes, ensuring test isolation.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(
        autocommit=False, autoflush=False, bind=connection
    )()

    # Begin a savepoint for nested transactions
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def mock_db() -> Generator[MagicMock, None, None]:
    """Create a mock database session for unit tests."""
    with patch("sqlalchemy.orm.Session") as mock_session:
        yield mock_session()


@pytest.fixture(scope="function")
def mock_file_model() -> MagicMock:
    """Create a mock File model for testing."""
    mock_file = MagicMock(spec=File)
    mock_file.id = 1
    mock_file.filename = "test.pdf"
    mock_file.filepath = "/tmp/test.pdf"
    mock_file.content_type = "application/pdf"
    mock_file.size = 1024
    mock_file.owner_id = 1
    mock_file.created_at = datetime.now(timezone.utc)
    mock_file.updated_at = datetime.now(timezone.utc)
    return mock_file


@pytest.fixture(scope="function")
def test_user(db_session: Session) -> Generator[User, None, None]:
    """
    Create a test user with hashed password.

    This fixture is function-scoped and will create a new user for each test.
    The user is automatically cleaned up after the test completes.
    """
    from datetime import datetime, timezone

    from app.core.security import get_password_hash

    # Create a unique identifier for this test user
    unique_id = str(uuid.uuid4().hex)[:8]
    email = f"test_user_{unique_id}@example.com"
    username = f"testuser_{unique_id}"

    # Create test user
    user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    try:
        yield user
    finally:
        # Cleanup
        try:
            db_session.delete(user)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            print(f"Error cleaning up test user: {e}")
        finally:
            db_session.close()


@pytest.fixture(scope="function")
def test_superuser(db_session: Session) -> Generator[User, None, None]:
    """
    Create a test superuser.

    This fixture is function-scoped and will create a new superuser for each test.
    The user is automatically cleaned up after the test completes.
    """
    from datetime import datetime, timezone

    from app.core.security import get_password_hash

    # Create a unique identifier for this test user
    unique_id = str(uuid.uuid4().hex)[:8]
    email = f"test_superuser_{unique_id}@example.com"
    username = f"testadmin_{unique_id}"

    # Create test superuser
    user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_superuser=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    try:
        yield user
    finally:
        # Cleanup
        try:
            db_session.delete(user)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            print(f"Error cleaning up test superuser: {e}")
        finally:
            db_session.close()


@pytest.fixture(scope="function")
def test_file(
    db_session: Session, test_user: User, temp_dir: Path
) -> Generator[File, None, None]:
    """
    Create a test file in the database and filesystem.

    This fixture is function-scoped and will create a new file for each test.
    The file is automatically cleaned up after the test completes.
    """
    # Create a unique filename to avoid conflicts
    unique_id = str(uuid.uuid4().hex)[:8]
    filename = f"test_file_{unique_id}.txt"

    # Create uploads directory if it doesn't exist
    uploads_dir = temp_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)

    # Create full file path
    filepath = uploads_dir / filename

    # Create test file with some content
    test_content = b"This is a test file"
    with open(filepath, "wb") as f:
        f.write(test_content)

    # Create file record in database
    file_record = File(
        filename=filename,
        filepath=str(filepath.relative_to(temp_dir)),  # Store relative path
        content_type="text/plain",
        size=len(test_content),
        owner_id=test_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db_session.add(file_record)
    db_session.commit()
    db_session.refresh(file_record)

    try:
        yield file_record
    finally:
        # Cleanup
        try:
            if filepath.exists():
                filepath.unlink()
            db_session.delete(file_record)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            print(f"Error cleaning up test file: {e}")
        finally:
            db_session.close()


@pytest.fixture(scope="function")
def authorized_client(client: TestClient, test_user: User) -> TestClient:
    """
    Create an authorized test client with a valid JWT token.
    """
    # Create access token with proper claims
    from datetime import timedelta

    from app.core.security import create_access_token

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = create_access_token(
        data={
            "sub": str(test_user.id),
            "username": test_user.username,
            "email": test_user.email,
            "is_superuser": test_user.is_superuser,
        },
        expires_delta=access_token_expires,
    )

    # Set authorization header
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


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
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
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
    original_get_db_fn = getattr(
        original_get_db, "_original_get_db", original_get_db
    )

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
def client(engine):
    """
    Provides a FastAPI TestClient for integration tests.
    Creates a new database session for each test and overrides the get_db dependency.
    """
    from fastapi.testclient import TestClient

    from app.api.deps import get_db
    from app.main import app

    # Create a new session for the test
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    # Override the get_db dependency
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides after the test
    app.dependency_overrides.clear()
