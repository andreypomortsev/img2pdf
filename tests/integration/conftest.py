"""Pytest configuration and fixtures for integration tests."""

import io
import os
import tempfile
import uuid
from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import get_password_hash
from app.db.base import Base
from app.models.file import File
from app.models.user import User


# Enable foreign key constraints for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """Set SQLite pragmas for better transaction support."""
    if dbapi_connection is not None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Create a SQLite database engine for testing."""
    # Use in-memory SQLite for testing
    database_url = "sqlite:///:memory:"
    print("\n=== Setting up test database ===")
    print("Using in-memory SQLite database")

    # Create engine with SQLite-specific settings
    engine = create_engine(
        database_url, connect_args={"check_same_thread": False}, echo=False
    )

    # Create all tables
    print("\n=== Creating database tables ===")

    # Drop all existing tables first (in case they exist)
    with engine.begin() as conn:
        # SQLite doesn't support DROP SCHEMA CASCADE, so we'll drop tables directly
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"DROP TABLE IF EXISTS {table.name}"))
        conn.execute(text("PRAGMA foreign_keys=ON"))

    # Create all tables
    Base.metadata.create_all(engine)

    # Verify tables were created
    with engine.connect() as conn:
        # Get the list of tables
        existing_tables = Base.metadata.tables.keys()
        print(f"=== Expected tables: {list(existing_tables)} ===")

        # Check if users table exists and get its columns
        if "users" not in existing_tables:
            raise RuntimeError(
                "Users table was not created in the test database"
            )

        # Get the columns from the users table
        result = conn.execute(text("PRAGMA table_info(users)"))
        columns = [
            row[1] for row in result
        ]  # Column name is the second item in the result

        # Verify required columns exist
        required_columns = {
            "id",
            "email",
            "username",
            "hashed_password",
            "is_active",
        }

        missing_columns = required_columns - set(columns)
        if missing_columns:
            raise RuntimeError(
                f"Missing required columns in users table: {missing_columns}"
            )

        # Insert a test user
        try:
            conn.execute(
                text(
                    """
                INSERT OR REPLACE INTO users (
                    id, email, username, hashed_password, full_name, 
                    is_active, is_superuser, created_at, updated_at
                ) VALUES (
                    :id, :email, :username, :hashed_password, :full_name, 
                    :is_active, :is_superuser, :created_at, :updated_at
                )
            """
                ),
                {
                    "id": 1,
                    "email": "test@example.com",
                    "username": "testuser",
                    "hashed_password": get_password_hash("testpassword"),
                    "full_name": "Test User",
                    "is_active": 1,
                    "is_superuser": 0,
                    "created_at": "2023-01-01T00:00:00",
                    "updated_at": "2023-01-01T00:00:00",
                },
            )
            conn.commit()
            print("=== Successfully inserted test user ===")

            # Verify the user was inserted
            result = conn.execute(text("SELECT * FROM users WHERE id = 1"))
            user_row = result.fetchone()
            if not user_row:
                raise RuntimeError("Failed to verify test user insertion")

            # Convert row to dict for better logging
            columns = [col[0] for col in result.cursor.description]
            user_dict = dict(zip(columns, user_row))
            print(f"=== Test user inserted: {user_dict} ===")

        except Exception as e:
            conn.rollback()
            print(f"ERROR: Failed to insert test user: {e}")
            raise

    # Make sure the engine is properly configured
    with engine.connect() as conn:
        # Verify foreign keys are enabled
        result = conn.execute(text("PRAGMA foreign_keys"))
        fk_enabled = result.scalar()
        print(f"=== Foreign keys enabled: {bool(fk_enabled)} ===")

        # Verify we can query the users table
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            print(f"=== Users table count: {count} ===")
        except Exception as e:
            print(f"ERROR: Failed to query users table: {e}")
            raise

    # Make the engine available to tests
    yield engine

    # Cleanup
    print("\n=== Cleaning up test database ===")
    engine.dispose()
    if os.path.exists(test_db_path):
        try:
            os.unlink(test_db_path)
            print("=== Test database file removed ===")
        except Exception as e:
            print(f"WARNING: Failed to remove test database file: {e}")


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test with automatic rollback."""
    connection = db_engine.connect()

    # Start a transaction
    transaction = connection.begin()

    # Create a session bound to the connection
    session = sessionmaker(
        autocommit=False, autoflush=False, bind=connection
    )()

    # Start a savepoint for nested transactions
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if not transaction.nested and not session._flushing:
            # If the transaction is not nested and we're not in the middle of a flush,
            # start a new transaction
            session.begin_nested()

    try:
        yield session

        # After the test, rollback any changes
        session.rollback()

    finally:
        # Always close the session and connection
        session.close()
        transaction.rollback()
        connection.close()


def override_get_db():
    """Override the get_db dependency to use our test database."""
    # Create a new session for each request
    db = None
    try:
        # Create a new connection and session for this request
        connection = db_engine.connect()
        transaction = connection.begin()
        session = sessionmaker(
            autocommit=False, autoflush=False, bind=connection
        )()

        # Begin a savepoint for nested transaction
        session.begin_nested()

        @event.listens_for(session, "after_transaction_end")
        def restart_savepoint(session, transaction):
            if transaction.nested and not transaction._parent.nested:
                session.begin_nested()

        yield session

    finally:
        if db is not None:
            try:
                session.close()
                transaction.rollback()
                connection.close()
            except Exception:
                pass


@pytest.fixture(scope="function")
def client(
    db_engine: Engine, monkeypatch
) -> Generator[TestClient, None, None]:
    """Create a test client that uses the test database."""
    # Set the test database URL in settings
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATABASE_URL", str(db_engine.url))

    # Create a new connection and transaction for this test
    connection = db_engine.connect()
    transaction = connection.begin()

    # Create a session bound to this connection
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=connection
    )

    def override_get_db():
        """Override the get_db dependency to use our test database."""
        db = None
        try:
            db = TestingSessionLocal()
            # Begin a savepoint for nested transaction
            db.begin_nested()

            @event.listens_for(db, "after_transaction_end")
            def restart_savepoint(session, transaction):
                if transaction.nested and not transaction._parent.nested:
                    session.begin_nested()

            yield db
        finally:
            if db is not None:
                db.close()

    # Create the FastAPI app
    from app.main import create_app

    app = create_app()

    # Override the database dependency to use our test database
    from app.db.session import get_db

    app.dependency_overrides[get_db] = override_get_db

    # Create a test client
    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_user(db_session: Session) -> Generator[User, None, None]:
    """Create a test user."""
    unique_id = str(uuid.uuid4())[:8]

    user = User(
        email=f"test_{unique_id}@example.com",
        username=f"testuser_{unique_id}",
        hashed_password=get_password_hash("testpassword"),
        full_name=f"Test User {unique_id}",
        is_active=True,
        is_superuser=False,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    yield user

    # Cleanup
    db_session.delete(user)
    db_session.commit()


@pytest.fixture(scope="function")
def test_superuser(db_session: Session) -> Generator[User, None, None]:
    """Create a test superuser."""
    unique_id = str(uuid.uuid4())[:8]

    user = User(
        email=f"admin_{unique_id}@example.com",
        username=f"admin_{unique_id}",
        hashed_password=get_password_hash("adminpassword"),
        full_name=f"Admin User {unique_id}",
        is_active=True,
        is_superuser=True,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    yield user

    # Cleanup
    db_session.delete(user)
    db_session.commit()


@pytest.fixture(scope="function")
def authorized_client(client: TestClient, test_user: User) -> TestClient:
    """Return an authorized client with a valid JWT token."""
    token = create_access_token(subject=test_user.id)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def test_image() -> bytes:
    """Generate a test image for upload tests."""
    img = Image.new("RGB", (22, 22), color="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
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


@pytest.fixture
def test_file(
    db_session: Session, test_user: User
) -> Generator[File, None, None]:
    """Create a test file in the database."""
    # Create a test file in the database
    file_data = b"test file content"
    file_record = File(
        filename="test_file.txt",
        content_type="text/plain",
        size=len(file_data),
        owner_id=test_user.id,
    )
    db_session.add(file_record)
    db_session.commit()
    db_session.refresh(file_record)

    # Create a temporary file with test content
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(file_data)
        temp_file_path = temp_file.name

    try:
        yield file_record
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        # Clean up the database record
        db_session.delete(file_record)
        db_session.commit()
