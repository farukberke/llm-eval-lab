import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from llm_eval_lab.api.deps import get_db
from llm_eval_lab.api.main import app
from llm_eval_lab.db import engine


@pytest.fixture
def db_session():
    """A Session bound to a connection-level transaction that is always
    rolled back, so tests never leave data behind — even if the code under
    test calls session.commit() (SAVEPOINTs absorb it)."""
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """A TestClient wired to the same transactional db_session, so router
    tests see their own writes and everything rolls back after the test —
    the get_db override yields db_session directly instead of committing/
    closing it, since db_session's own teardown owns that lifecycle."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
