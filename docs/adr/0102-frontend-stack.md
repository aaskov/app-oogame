# 0102 — Frontend stack

**Status:** Accepted · 2026-10-18

## Context

The gate slots check the backend (ADR 0100). The frontend needs the same
five slots, in the same devcontainer and in CI.

## Decision

- **Runtime:** Next.js 16 (App Router), React 19, TypeScript, Tailwind 4.
  Node 24 LTS, pinned in `mise.toml`. `@types/node` matches Node 24.
- **Packages:** `package-lock.json`, installed with `npm ci` by
  `.mise/setup.d/20-frontend`. npm blocks install scripts by default. The
  postinstall script of `unrs-resolver` is denied in `package.json`
  (`allowScripts`), because npm already installs its native binary.
- **Slots:**

  | Slot | Tool |
  |------|------|
  | lint | `eslint --max-warnings 0 --no-inline-config`. `ban-ts-comment` catches `@ts-ignore`. |
  | types | `next typegen`, then `tsc --noEmit` |
  | test | vitest with jsdom and Testing Library |
  | boundaries | dependency-cruiser: no circular imports, feature isolation in `components/`, no UI imports in `lib/` and `types/` |
  | contracts | `src/types/api.ts` must equal a fresh openapi-typescript generation from `contracts/openapi.yaml` |

- **Architect-owned:** `src/lib/` and `src/types/`, as in the first version
  of app-oogame. The API client in `src/lib/` is the frontend side of the contract.
- **Guarded:** the manifests, the lock file, and each tool config.
- **Each slot returns exit 1 on a tool failure,** whatever exit code the tool
  uses (tsc uses 2).

## Consequences

- An agent cannot weaken a rule with an inline comment.
- A contract change needs `npm run types:api` by the architect. Otherwise
  `check:contracts` fails.
- The gate takes about 20 seconds. Most of it is the seeded-violation cases.
