"""Shared test fixtures (docs/adr/0104, 0108). Architect-owned (CODEOWNERS).

Tests use their own database, <name>_test, never the development database.
So data from manual use of the app (the browser, curl) cannot break a test.

Each test runs in a transaction that is rolled back at the end. Tests do not
see each other's data, and they leave the database unchanged. This matters,
because the gate and the guardrail tests run at the same time.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy.orm import Session

from app.shared.db import get_engine, get_session

BACKEND = Path(__file__).resolve().parents[1]
# Serializes the setup when the gate and the guardrail tests start at the same time.
SETUP_LOCK = 0x0A6E5EED


def pytest_configure(config: pytest.Config) -> None:
    """Switch to the test database before a test module reads the settings."""
    development_url = os.environ["DATABASE_URL"]
    server_url, name = development_url.rsplit("/", 1)
    test_name = name if name.endswith("_test") else f"{name}_test"
    os.environ["DATABASE_URL"] = f"{server_url}/{test_name}"

    with psycopg.connect(development_url, autocommit=True) as admin:
        admin.execute("select pg_advisory_lock(%s)", (SETUP_LOCK,))
        try:
            exists = admin.execute(
                "select 1 from pg_database where datname = %s", (test_name,)
            ).fetchone()
            if not exists:
                admin.execute(sql.SQL("create database {}").format(sql.Identifier(test_name)))
            alembic = Config(str(BACKEND / "alembic.ini"))
            alembic.set_main_option("script_location", str(BACKEND / "migrations"))
            command.upgrade(alembic, "head")
        finally:
            admin.execute("select pg_advisory_unlock(%s)", (SETUP_LOCK,))


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
    from app.main import create_app  # After pytest_configure: the app reads the test database.

    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
