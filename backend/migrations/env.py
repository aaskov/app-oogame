"""Alembic environment (docs/adr/0104). Guarded."""

from alembic import context
from sqlalchemy import create_engine, pool

from app.shared.config import get_settings
from app.shared.db import sqlalchemy_url
from app.shared.orm import Base

target_metadata = Base.metadata


def run_migrations() -> None:
    # NullPool: close the connection at the end. A pooled one stays open after the migration.
    engine = create_engine(sqlalchemy_url(get_settings().database_url), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
