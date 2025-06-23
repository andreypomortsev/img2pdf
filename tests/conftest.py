import os

os.environ["TESTING"] = "True"

from unittest.mock import patch

import pytest
from celery.backends.database.models import ResultModelBase
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.worker import celery_app

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Set up Celery, test database schema, and result backend tables once per session.
    """
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        result_backend=settings.CELERY_RESULT_BACKEND,
    )

    # Create all tables for the app and for the celery backend
    Base.metadata.create_all(bind=engine)
    ResultModelBase.metadata.create_all(bind=engine)

    yield

    # Teardown
    ResultModelBase.metadata.drop_all(bind=engine)
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(settings.DATABASE_URL.split("///")[1]):
        os.remove(settings.DATABASE_URL.split("///")[1])


@pytest.fixture(scope="function")
def db_session():
    """
    Provide a transactional scope around a test function.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    Provide a test client that uses the same transactional session as the tests.
    """

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    from contextlib import contextmanager

    @contextmanager
    def override_task_session_scope():
        yield db_session

    # Patch the SessionLocal used by Celery tasks to ensure they participate
    # in the same transaction as the test.
    with patch("app.tasks.SessionLocal", override_task_session_scope):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
