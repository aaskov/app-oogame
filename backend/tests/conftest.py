"""Shared test fixtures (docs/adr/0104). Architect-owned (CODEOWNERS).

Each test runs in a transaction that is rolled back at the end. Tests do not
see each other's data, and they leave the database unchanged. This matters,
because the gate and the guardrail tests run at the same time.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import create_app
from app.shared.db import get_engine, get_session


@pytest.fixture
def session() -> Iterator[Session]:
    connection = get_engine().connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
