# 0104 — Data access: SQLAlchemy, Alembic, and a dependencies layer

**Status:** Accepted · 2026-10-18

## Context

Auth is the first feature with a table. ADR 0103 left the ORM and the
migration tool open. Agents must not change the schema, and the layer rules
(ADR 0101) forbid the router and the service to import the database.

## Decision

- **SQLAlchemy 2** for the tables, in `app/shared/orm/` (architect-owned), as
  in the first version of app-oogame. Repositories read and write these classes.
- **Alembic** for the schema, in `backend/migrations/` (architect-owned).
  `.mise/setup.d/30-migrate` runs `alembic upgrade head` in each new container
  and in CI. Only the architect writes a migration.
- **`app/shared/db.py`:** one engine, and `get_session()` for `Depends()`.
- **A `dependencies` layer** between router and service. It holds the
  `Depends()` providers that build a service from a repository and a session.
  The layers are: `router → dependencies → service → repository → schemas | models`.
- **Only `dependencies` and `repository` import** `app.shared.db`,
  `app.shared.orm`, `sqlalchemy`, or `psycopg` (import-linter).
- **Tests run in a transaction that rolls back** (`tests/conftest.py`,
  architect-owned): the `session` and `client` fixtures.

## Consequences

- A new table needs an ORM class and a migration from the architect, before
  an agent works on the feature.
- Tests do not see each other's data. The gate and the guardrail tests can
  share one database at the same time.
- Generated migrations are excluded from ruff. The architect reviews them.
