import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.file import File
from app.models.user import User


@pytest.fixture(scope="module")
def test_engine():
    """Create a test database engine with in-memory SQLite."""
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Clean up
    engine.dispose()


def test_db_connection(test_engine):
    """Test database connection."""
    with test_engine.connect() as connection:
        assert connection is not None


def test_db_tables_exist(test_engine):
    """Test that required tables exist."""
    inspector = inspect(test_engine)
    tables = inspector.get_table_names()

    # Check that all expected tables exist
    expected_tables = ["users", "files"]  # Add other table names as needed
    for table in expected_tables:
        assert table in tables, f"Table {table} does not exist"


def test_models_can_be_created(test_engine):
    """Test that models can be created in the test database."""
    # Create a new session
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    with TestingSessionLocal() as db:
        # Test User model
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashedpassword",
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        db.commit()

        # Test File model
        file = File(
            filename="test.txt",
            filepath="/test/test.txt",
            content_type="text/plain",
            size=123,
            owner_id=user.id,
        )
        db.add(file)
        db.commit()

        # Verify data was saved
        assert user.id is not None
        assert file.id is not None
        assert file.owner_id == user.id
