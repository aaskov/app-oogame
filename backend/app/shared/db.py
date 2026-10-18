"""Database access for all modules (docs/adr/0103, 0104). Architect-owned (CODEOWNERS).

Only a module's dependencies and repository layers import this file (docs/adr/0101).
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.shared.config import get_settings


def sqlalchemy_url(database_url: str) -> str:
    """Use the psycopg 3 driver for a plain postgresql:// URL."""
    return database_url.replace("postgresql://", "postgresql+psycopg://", 1)


@lru_cache
def get_engine() -> Engine:
    return create_engine(sqlalchemy_url(get_settings().database_url))


def get_session() -> Iterator[Session]:
    """A session for one request. Use it with Depends(). The tests override it."""
    with Session(get_engine()) as session:
        yield session
