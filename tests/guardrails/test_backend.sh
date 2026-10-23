#!/usr/bin/env bash
# Seeded violations for the backend slots (docs/adr/0100, docs/adr/0101).
# Each case runs a slot against a copy of backend/ and contracts/, never
# against the real tree, because the checks run in parallel.
set -uo pipefail

# shellcheck source=tests/guardrails/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [ ! -x "$repo/backend/.venv/bin/python" ]; then
  echo "test_backend: backend/.venv is missing. Run 'mise run setup'."
  exit 1
fi

root="$tmp/root"
b="$root/backend"

# A fresh copy of backend/ and contracts/, without the virtual environment.
fresh() {
  rm -rf "$root" && mkdir -p "$root"
  tar -C "$repo" --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache \
    --exclude=.ruff_cache -cf - backend contracts .github/CODEOWNERS | tar -C "$root" -xf -
}
# The copy gets its own database (guardrails_test), so that its tests and the
# gate's own check:test, which run at the same time, never share rows.
slot() {
  if [ -n "${DATABASE_URL:-}" ]; then
    SEED_ROOT="$root" DATABASE_URL="${DATABASE_URL%/*}/guardrails" "$checks/$1"
  else
    SEED_ROOT="$root" "$checks/$1"
  fi
}

# A second module, so that the boundary contracts have something to compare.
alpha_module() {
  mkdir -p "$b/app/modules/alpha/_internal"
  touch "$b/app/modules/alpha/__init__.py" "$b/app/modules/alpha/_internal/__init__.py"
  printf '%s\n' "$1" >"$b/app/modules/alpha/_internal/service.py"
}

# --- a clean copy passes each slot --------------------------------------------

for name in lint types test boundaries contracts; do
  fresh
  expect 0 "check:$name passes on a clean copy" slot "$name"
done

# --- check:lint ---------------------------------------------------------------

fresh; printf 'import os\n' >"$b/app/seeded.py"
expect 1 "check:lint fails on an unused import" slot lint

fresh; printf 'import os  # noqa\n' >"$b/app/seeded.py"
expect 1 "check:lint fails on a bare noqa comment" slot lint

# --- check:types --------------------------------------------------------------

fresh; printf 'value: int = "text"\n' >"$b/app/seeded.py"
expect 1 "check:types fails on a type error" slot types

fresh; printf 'value: int = "text"  # pyright: ignore[reportAssignmentType]\n' >"$b/app/seeded.py"
expect 1 "check:types fails on a pyright ignore outside a guarded path" slot types

fresh; printf 'value: int = "text"  # pyright: ignore[reportAssignmentType]\n' >"$b/app/shared/seeded.py"
expect 0 "check:types allows a pyright ignore in a guarded path" slot types

fresh; printf 'value: int = "text"  # type: ignore\n' >"$b/app/seeded.py"
expect 1 "check:types does not accept a type: ignore comment" slot types

# --- check:test ---------------------------------------------------------------

fresh; printf 'def test_seeded() -> None:\n    assert 1 == 2\n' >"$b/tests/test_seeded.py"
expect 1 "check:test fails on a failing test" slot test

fresh; printf 'import warnings\n\n\ndef test_seeded() -> None:\n    warnings.warn("seeded", DeprecationWarning, stacklevel=1)\n' >"$b/tests/test_seeded.py"
expect 1 "check:test fails on a warning" slot test

# --- check:boundaries ---------------------------------------------------------

fresh; alpha_module 'from app.modules.health._internal import service'
expect 1 "check:boundaries fails on an import of another module's _internal" slot boundaries

fresh; alpha_module 'from app.modules.health import public_api'
expect 0 "check:boundaries allows an import of another module's public_api" slot boundaries

fresh; printf '\nfrom app.modules.health._internal import router\n' >>"$b/app/modules/health/_internal/service.py"
expect 1 "check:boundaries fails when a service imports its router" slot boundaries

fresh; printf '\nfrom app.modules.health._internal import service\n' >>"$b/app/modules/health/_internal/schemas.py"
expect 1 "check:boundaries fails when schemas import the service" slot boundaries

fresh; printf '\nfrom app.shared import db\n' >>"$b/app/modules/health/_internal/service.py"
expect 1 "check:boundaries fails when a service imports the database" slot boundaries

fresh; printf 'from app.shared import db\n' >"$b/app/modules/health/_internal/repository.py"
expect 0 "check:boundaries allows a repository to import the database" slot boundaries

# --- check:contracts ----------------------------------------------------------

fresh; printf '  /seeded:\n    get:\n      responses:\n        "200":\n          description: Seeded.\n' \
  | sed -i '/^paths:$/r /dev/stdin' "$root/contracts/openapi.yaml"
expect 1 "check:contracts fails when the backend lacks a contract operation" slot contracts

fresh; printf '\n\n@router.get("/seeded")\ndef read_seeded() -> Health:\n    return Health(status="ok")\n' \
  >>"$b/app/modules/health/_internal/router.py"
expect 1 "check:contracts fails when the backend serves an operation that is not in the contract" slot contracts

fresh; printf '  /seeded:\n    get:\n      x-planned: true\n      responses:\n        "200":\n          description: Seeded.\n' \
  | sed -i '/^paths:$/r /dev/stdin' "$root/contracts/openapi.yaml"
expect 0 "check:contracts allows a missing operation that is x-planned" slot contracts

# --- schemas (docs/adr/0110) ---------------------------------------------------

fresh; sed -i 's/^    password: Annotated\[str, StringConstraints(min_length=8, max_length=128)\]$/    password: Annotated[str, StringConstraints(min_length=8, max_length=128)] | None = None/' \
  "$b/app/modules/auth/_internal/schemas.py"
expect 1 "check:contracts fails when the backend accepts null for a contract field" slot contracts

# Lesson 20: the check does not compare a planned operation, but null still fails.
fresh; sed -i 's/^      operationId: list_buildings$/      operationId: list_buildings\n      x-planned: true/; s/^      operationId: upgrade_building$/      operationId: upgrade_building\n      x-planned: true/' \
  "$root/contracts/openapi.yaml"
sed -i 's/upgrade_finishes_at: datetime | SkipJsonSchema\[None\] = None/upgrade_finishes_at: datetime | None = None/' \
  "$b/app/modules/planets/_internal/schemas.py"
expect 1 "check:contracts fails on null in a planned operation" slot contracts

fresh; sed -i 's/min_length=8, max_length=128/max_length=128/' "$b/app/modules/auth/_internal/schemas.py"
expect 1 "check:contracts fails when the backend lacks a contract constraint" slot contracts

fresh; sed -i 's/^    responses={401: {"model": ErrorOut}},$/    responses={401: {"model": ErrorOut}, 403: {"model": ErrorOut}},/' \
  "$b/app/modules/auth/_internal/router.py"
expect 1 "check:contracts fails when the backend has a response code that is not in the contract" slot contracts

# --- the dependencies layer (docs/adr/0104) ------------------------------------

fresh; printf 'from app.shared.db import get_session\n' >"$b/app/modules/health/_internal/dependencies.py"
expect 0 "check:boundaries allows the dependencies layer to import the database" slot boundaries

fresh; printf '\nfrom sqlalchemy.orm import Session\n' >>"$b/app/modules/health/_internal/service.py"
expect 1 "check:boundaries fails when a service imports sqlalchemy" slot boundaries

fresh; printf 'from app.modules.health._internal import router\n' >"$b/app/modules/health/_internal/dependencies.py"
expect 1 "check:boundaries fails when dependencies imports the router" slot boundaries

guardrails_result test_backend
