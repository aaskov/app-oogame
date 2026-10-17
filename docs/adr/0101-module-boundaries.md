# 0101 — Module boundaries

**Status:** Accepted · 2026-10-17

## Context

The backend is a modular monolith. In the first version of app-oogame, the
boundary rules were prose in AGENTS.md, and no machine enforced them.

## Decision

import-linter enforces two contracts in `backend/pyproject.toml`:

1. **Independence:** the modules in `app.modules.*` do not import each other.
   The one exception is an import of another module's `public_api`.
2. **Layers:** in each `app.modules.*._internal`, the import direction is
   `router → service → repository → schemas | models`. Each layer is
   optional: the contract sets the direction, not the presence.

`schemas` and `models` are siblings in the lowest layer. They do not import
each other.

## Consequences

- A cross-module call goes through `public_api.py`. The architect owns what
  each `public_api.py` exposes.
- The rules hold for each new module without a config change, because the
  contracts use wildcards.
- `tests/guardrails/test_backend.sh` proves each contract with a seeded violation.
