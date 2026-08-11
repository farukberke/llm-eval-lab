import pytest
from sqlalchemy.orm import Session

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
