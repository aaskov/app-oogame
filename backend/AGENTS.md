# backend/AGENTS.md

FastAPI modular monolith. `CLAUDE.md` is a link to this file.
Decisions: `docs/adr/0100` (stack) and `docs/adr/0101` (module boundaries).

## Module layout

```
app/modules/<module>/
  public_api.py     ← the only file that other modules and app/main.py import
  _internal/
    router.py       ← HTTP only. No business logic.
    service.py      ← business logic
    repository.py   ← database access
    schemas.py      ← Pydantic models (model_config from_attributes=True)
    models.py       ← plain dataclasses. No ORM, no I/O.
tests/              ← tests for the backend
```

Each layer imports only from layers below it:
`router → service → repository → schemas | models`. A module can omit a layer.
Inject dependencies with `Depends()`. Do not create them inside a function body.

## Checks (all in `mise run check`)

| Check | Tool | Notes |
|-------|------|-------|
| `check:lint` | ruff | A bare `# noqa` fails. Name the rule. |
| `check:types` | basedpyright | `# type: ignore` has no effect. Fix the type. |
| `check:test` | pytest | A warning fails the test run. |
| `check:boundaries` | import-linter | Modules meet only through `public_api.py`. |
| `check:contracts` | `.mise/lib/contract_check.py` | The app serves exactly the operations in `contracts/openapi.yaml`. |

You cannot change `pyproject.toml` or `uv.lock`. If you need a package or a
config change, follow "When you are blocked" in the root `AGENTS.md`.

Run a single tool: `cd backend && uv run pytest -q`.
