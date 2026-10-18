# 0103 — Postgres as a devcontainer sidecar

**Status:** Accepted · 2026-10-18

## Context

The backend needs a database for its first real features. In the first
version of app-oogame, Postgres ran in a separate platform stack with host
ports, and parallel worktrees clashed on those ports.

## Decision

- The devcontainer uses Docker Compose (`.devcontainer/compose.yml`) with
  two services: `dev` (the agent environment) and `db` (Postgres 18).
- **No host ports.** The backend reaches `db:5432` on the compose network.
  Each clone gets its own compose project, so parallel agents get separate
  databases and do not clash.
- `dev` waits for the `db` health check (`pg_isready`), so tests do not run
  before the database is ready.
- A named volume for each compose project keeps the data across rebuilds.
- `DATABASE_URL` is set in the `dev` service. `app/shared/db.py` (guarded)
  is the only connection helper.
- **Only a repository accesses the database.** An import-linter contract
  forbids `app.shared.db` and `psycopg` in router, service, schemas, and models.
- **No ORM yet.** psycopg 3 only. The ORM choice belongs to the first
  feature with tables, and it is a decision for the architect.
- The workspace path is `/workspace`, because Compose cannot read the folder
  name variable of the devcontainer.

## Consequences

- CI runs the same compose setup, so `check:test` includes the database test.
- Schema migrations are not decided yet. Agents must not run them (as in the
  first version). A migration tool is a later ADR.
- The default credentials (`app` / `app`) are for local development only.
