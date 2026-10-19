# 0108 — Tests use their own database

**Status:** Accepted · 2026-10-19

## Context

After the architect used the app by hand (ADR 0106), the local gate failed:
a test expected an empty `users` table, but the development database had a
user from the browser. CI and fresh agent clones passed, because their
databases were empty. A test must not depend on development data.

## Decision

- `tests/conftest.py` switches `DATABASE_URL` to `<name>_test` in
  `pytest_configure`, before a test module reads the settings.
- It creates the test database if it is missing, and runs `alembic upgrade
  head` on it. A Postgres advisory lock serializes this setup, because the
  gate and the guardrail tests start pytest at the same time.
- Each test still runs in a transaction that rolls back (ADR 0104).
- `test_tests_use_their_own_database` proves that the tests use `*_test`.
- `migrations/env.py` uses `NullPool`, so a migration leaves no open connection.

## Consequences

- Manual use of the app cannot break the gate.
- A new migration reaches the test database at the next test run, without a
  container rebuild.
