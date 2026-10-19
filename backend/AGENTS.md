# backend/AGENTS.md

FastAPI modular monolith. `CLAUDE.md` is a link to this file.
Decisions: `docs/adr/0100` (stack) and `docs/adr/0101` (module boundaries).

## Module layout

```
app/modules/<module>/
  public_api.py     ← the only file that other modules and app/main.py import
  _internal/
    router.py       ← HTTP only. No business logic.
    dependencies.py ← Depends() providers that build the service (session → repository → service)
    service.py      ← business logic
    repository.py   ← database access
    schemas.py      ← Pydantic models (model_config from_attributes=True)
    models.py       ← plain dataclasses. No ORM, no I/O.
tests/              ← tests for the backend
```

Each layer imports only from layers below it:
`router → dependencies → service → repository → schemas | models`. A module can omit a layer.
Inject dependencies with `Depends()`. Do not create them inside a function body.

## Database

Postgres runs next to the devcontainer (`docs/adr/0103`, `docs/adr/0104`).

- The tables are SQLAlchemy classes in `app/shared/orm/`. You cannot change them.
- A repository takes a `Session` and reads or writes those classes.
- `dependencies.py` gets the session with `Depends(app.shared.db.get_session)`.
- Only `dependencies.py` and `repository.py` import the database or SQLAlchemy.
- Do not write or run migrations. If you need a column, ask with `needs-decision`.

## The logged-in user

To know who calls an endpoint, use the provider from the auth module:
`Depends(app.modules.auth.public_api.get_current_user_id)`. It returns the
user ID, or it raises 401 (`docs/adr/0109`). Import it in `dependencies.py`
or `router.py`. Never take a user ID from the URL or the body.

If a URL names a resource that a user owns, for example a planet, load it
with both its ID and the user ID. If it belongs to a different user, return
the same 404 as for an ID that does not exist.

## Tests

`tests/conftest.py` gives two fixtures. Tests use their own database
(`app_test`, `docs/adr/0108`), and each test runs in a transaction that rolls
back, so tests do not see each other's data or development data.

- `client`: a `TestClient` for the app, with the test session.
- `session`: the SQLAlchemy session of the test.

## Settings

`app.shared.config.get_settings()` has `jwt_secret`, `jwt_expires_minutes`,
`session_cookie_name`, and `session_cookie_secure` (`docs/adr/0105`).

## Checks (all in `mise run check`)

| Check | Tool | Notes |
|-------|------|-------|
| `check:lint` | ruff | A bare `# noqa` fails. Name the rule. |
| `check:types` | basedpyright | `# type: ignore` has no effect. Fix the type. |
| `check:test` | pytest | A warning fails the test run. |
| `check:boundaries` | import-linter | Modules meet only through `public_api.py`. |
| `check:contracts` | `.mise/lib/contract_check.py` | The app serves exactly the operations in `contracts/openapi.yaml`, with equal schemas (`docs/adr/0110`). Each failure line names the field to fix. |

You cannot change `pyproject.toml` or `uv.lock`. If you need a package or a
config change, follow "When you are blocked" in the root `AGENTS.md`.

Run a single tool: `cd backend && uv run pytest -q`.
