#!/usr/bin/env bash
# Seeded violations for the frontend slots (docs/adr/0102).
# Each case runs a slot against a copy of frontend/ and contracts/, never
# against the real tree, because the checks run in parallel.
set -uo pipefail

# shellcheck source=tests/guardrails/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [ ! -d "$repo/frontend/node_modules" ]; then
  echo "test_frontend: frontend/node_modules is missing. Run 'mise run setup'."
  exit 1
fi

root="$tmp/root"
f="$root/frontend"

# A fresh copy of frontend/ and contracts/. node_modules is a link to the real one.
fresh() {
  rm -rf "$root" && mkdir -p "$root"
  tar -C "$repo" --exclude=node_modules --exclude=.next --exclude='*.tsbuildinfo' \
    -cf - frontend contracts .github/CODEOWNERS | tar -C "$root" -xf -
  ln -s "$repo/frontend/node_modules" "$f/node_modules"
}
slot() { SEED_ROOT="$root" "$checks/$1"; }

# --- a clean copy passes each slot --------------------------------------------

for name in lint types test boundaries contracts; do
  fresh
  expect 0 "check:$name passes on a clean copy (frontend)" slot "$name"
done

# --- check:lint ---------------------------------------------------------------

fresh; printf 'export function seeded() {\n  const unused = 1;\n}\n' >"$f/src/lib/seeded.ts"
expect 1 "check:lint fails on an unused variable" slot lint

fresh; printf '/* eslint-disable */\nexport function seeded() {\n  const unused = 1;\n}\n' >"$f/src/lib/seeded.ts"
expect 1 "check:lint does not accept an eslint-disable comment" slot lint

fresh; printf '// @ts-ignore\nexport const seeded: number = "text";\n' >"$f/src/lib/seeded.ts"
expect 1 "check:lint fails on a @ts-ignore comment" slot lint

# --- check:types --------------------------------------------------------------

fresh; printf 'export const seeded: number = "text";\n' >"$f/src/lib/seeded.ts"
expect 1 "check:types fails on a type error" slot types

# --- check:test ---------------------------------------------------------------

fresh; printf 'import { expect, it } from "vitest";\n\nit("seeded", () => {\n  expect(1).toBe(2);\n});\n' \
  >"$f/src/lib/seeded.test.ts"
expect 1 "check:test fails on a failing test" slot test

# --- check:boundaries ---------------------------------------------------------

fresh; mkdir -p "$f/src/components/alpha"
printf 'import { HealthStatus } from "@/components/health/HealthStatus";\n\nexport const Seeded = HealthStatus;\n' \
  >"$f/src/components/alpha/Seeded.tsx"
expect 1 "check:boundaries fails when a feature imports another feature" slot boundaries

fresh; printf 'import { HealthStatus } from "@/components/health/HealthStatus";\n\nexport const seeded = HealthStatus;\n' \
  >"$f/src/lib/seeded.ts"
expect 1 "check:boundaries fails when lib/ imports a component" slot boundaries

fresh; printf 'import { b } from "./seeded-b";\n\nexport const a = () => b;\n' >"$f/src/lib/seeded-a.ts"
printf 'import { a } from "./seeded-a";\n\nexport const b = () => a;\n' >"$f/src/lib/seeded-b.ts"
expect 1 "check:boundaries fails on a circular import" slot boundaries

# --- check:contracts ----------------------------------------------------------

fresh; printf '  /seeded:\n    get:\n      responses:\n        "200":\n          description: Seeded.\n' \
  | sed -i '/^paths:$/r /dev/stdin' "$root/contracts/openapi.yaml"
expect 1 "check:contracts fails when src/types/api.ts is older than the contract" slot contracts

fresh; printf '\nexport type Seeded = string;\n' >>"$f/src/types/api.ts"
expect 1 "check:contracts fails on a manual change to src/types/api.ts" slot contracts

# Lesson 17: each contract schema has an export in src/lib/api.ts.
fresh; sed -i '/^export type Energy = /d' "$f/src/lib/api.ts"
expect 1 "check:contracts fails when src/lib/api.ts does not export a schema" slot contracts

fresh; printf '// @ts-expect-error seeded\nexport const seeded: number = "text";\n' >"$f/src/seeded.ts"
expect 1 "check:types fails on a @ts-expect-error outside a guarded path" slot types

guardrails_result test_frontend
