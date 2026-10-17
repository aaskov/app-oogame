# 0100 — Backend stack

**Status:** Accepted · 2026-10-17

App ADRs start at 0100. Numbers 0001–0099 are for decisions from agentic-seed.

## Context

The gate has five empty slots (seed ADR 0003). The backend needs tools that
fill them and run the same way in the devcontainer and in CI.

## Decision

- **Runtime:** Python 3.13 and FastAPI. uv installs Python from
  `backend/.python-version`. mise pins only `uv` and `node`.
- **Packages:** `uv.lock`, installed with `uv sync --locked` by
  `.mise/setup.d/10-backend`. A change to the lock file is a decision for
  the architect.
- **Slots:**

  | Slot | Tool |
  |------|------|
  | lint | ruff (`E F I B UP PGH RUF`). PGH004 forbids a bare `# noqa`. |
  | types | basedpyright, standard mode, `enableTypeIgnoreComments = false` |
  | test | pytest with `filterwarnings = error` |
  | boundaries | import-linter (ADR 0101) |
  | contracts | `.mise/lib/contract_check.py`: served operations = contract operations |

- **basedpyright, not pyright:** the PyPI `pyright` package downloads its
  engine at the first run. basedpyright has the engine in the wheel, so
  `uv.lock` pins it fully and CI does not depend on a runtime download.
- **httpx2:** Starlette's test client deprecates `httpx` in favor of `httpx2`.
- **Guarded:** `pyproject.toml`, `uv.lock`, `.python-version`, and the
  contract check. Otherwise an agent can weaken a check or add a package.
- **Slots run tools from the real repository against `SEED_ROOT`.** The
  guardrail tests (`tests/guardrails/test_backend.sh`) run each slot against
  a copy that has a seeded violation.

## Consequences

- An agent cannot add a package. It asks with `needs-decision`.
- `check:contracts` compares methods and paths only, not the schemas. A
  stronger check (for example schemathesis) is a later decision.
- No coverage limit yet. Add one when there is enough code to set a fair level.
