<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# frontend/AGENTS.md

Next.js App Router, TypeScript, Tailwind, mobile-first. `CLAUDE.md` is a link
to this file. The block above belongs to Next.js: `next dev` writes it again.
Decision: `docs/adr/0102`.

## Layout

```
src/app/(game)/<feature>/   ← routes for a feature
src/components/<feature>/   ← components for a feature, with *.test.tsx
src/hooks/use<Feature>.ts   ← hooks for a feature
src/lib/                    ← shared code, for example the API client. Architect-owned.
src/types/api.ts            ← generated from contracts/openapi.yaml. Do not edit.
```

A feature folder in `components/` does not import another feature folder.
`lib/` and `types/` do not import UI code. There are no circular imports.

## Checks (all in `mise run check`)

| Check | Tool | Notes |
|-------|------|-------|
| `check:lint` | eslint | Warnings fail. `eslint-disable` comments have no effect. |
| `check:types` | tsc | `@ts-ignore` fails `check:lint`. Fix the type. |
| `check:test` | vitest | Tests are `src/**/*.test.{ts,tsx}`. |
| `check:boundaries` | dependency-cruiser | The rules above. |
| `check:contracts` | openapi-typescript | `src/types/api.ts` must match the contract. |

You cannot change `package.json`, `package-lock.json`, or the tool configs.
If you need a package or a config change, follow "When you are blocked" in
the root `AGENTS.md`.

Run a single tool: `cd frontend && npm run test`.
