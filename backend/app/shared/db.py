"""Database access for all modules (docs/adr/0103). Architect-owned (CODEOWNERS).

Only a module's repository layer imports this file (docs/adr/0101).
"""

import os

import psycopg


def database_url() -> str:
    return os.environ["DATABASE_URL"]


def connect() -> psycopg.Connection:
    return psycopg.connect(database_url())
