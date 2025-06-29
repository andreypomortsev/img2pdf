"""Pytest configuration and fixtures for integration tests."""

import os
import tempfile
import uuid
from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import create_access_token, get_password_hash
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
    """Create a PostgreSQL database engine for testing."""
    # Use PostgreSQL for testing to match production environment
    database_url = "postgresql://user:password@db/mydatabase_test"
    print("\n=== Setting up test database ===")
    print(f"Database URL: {database_url}")

    # Wait for PostgreSQL to be ready
    import time

    from sqlalchemy.exc import OperationalError

    max_retries = 10
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            # Test connection
            temp_engine = create_engine(database_url)
            with temp_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except OperationalError as e:
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Failed to connect to PostgreSQL after {max_retries} attempts"
                ) from e
            print(
                f"PostgreSQL not ready, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})"
            )
            time.sleep(retry_delay)

    # Create engine with connection pooling for PostgreSQL
    engine = create_engine(
        database_url,
        echo=bool(os.getenv("SQL_ECHO")),
        pool_pre_ping=True,  # Enable connection health checks
        pool_size=5,  # Number of connections to keep open
        max_overflow=10,  # Max number of connections beyond pool_size
    )

    # Create all tables
    print("\n=== Creating database tables ===")

    # Import all models to ensure they are registered with SQLAlchemy
    from app.models import file, user  # noqa: F401

    # Drop all tables first to ensure a clean state
    Base.metadata.drop_all(bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Get the list of tables that should exist
    expected_tables = list(Base.metadata.tables.keys())
    print(f"=== Expected tables: {expected_tables} ===")

    # Verify tables were created
    with engine.connect() as conn:
        # Verify tables exist
        result = conn.execute(
            text(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                """
            )
        )
        tables = [row[0] for row in result]
        print(f"=== Actual tables in database: {tables} ===")

        # Verify all expected tables exist
        missing_tables = set(expected_tables) - set(tables)
        if missing_tables:
            raise RuntimeError(f"Missing tables in database: {missing_tables}")

        # Verify the users table exists and has the expected columns
        if "users" not in tables:
            raise RuntimeError("Users table not found in database")

        # Get columns for users table
        result = conn.execute(
            text(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
                """
            )
        )
        columns = [row[0] for row in result]
        print(f"=== Users table columns: {columns} ===")

        # Verify required columns exist
        required_columns = {"id", "email", "username", "hashed_password", "is_active"}
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
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

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
        session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

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
def client(db_engine: Engine, monkeypatch) -> Generator[TestClient, None, None]:
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


@pytest.fixture(scope="function")
def test_file(db_session: Session, test_user: User) -> Generator[File, None, None]:
    """Create a test file in the database."""
    unique_id = str(uuid.uuid4())[:8]
    file_path = f"test_file_{unique_id}.pdf"
    temp_dir = None

    try:
        # Create a temporary file for testing
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, file_path)
        with open(temp_file, "wb") as f:
            f.write(b"Test file content")

        file_obj = File(
            filename=file_path,
            filepath=temp_file,  # Changed from file_path to filepath
            content_type="application/pdf",
            size=os.path.getsize(temp_file),
            owner_id=test_user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        db_session.add(file_obj)
        db_session.commit()
        db_session.refresh(file_obj)

        yield file_obj

    finally:
        # Clean up the database
        if "file_obj" in locals():
            db_session.delete(file_obj)
            db_session.commit()

        # Clean up the temporary files
        if temp_dir and os.path.exists(temp_dir):
            try:
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                os.rmdir(temp_dir)
            except Exception as e:
                print(f"Error cleaning up temp files: {e}")
    return file_obj
