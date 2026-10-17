# 0004 — Derive the project state. Do not write it by hand.

**Status:** Accepted · 2026-10-15

## Context

A hand-written status file is correct only right after someone updates
it. A lazy-proof process cannot depend on such a file.

## Decision

The project state comes from sources that change when the work changes:

| Need | Source |
|------|--------|
| What is the next task? | GitHub issues |
| What is blocked? | Issues with the label `needs-decision` |
| What is in progress? | Branches, worktrees, and open PRs |
| What was done, and why? | Merged PR descriptions and `docs/adr/` |
| Is it healthy? | CI on `main` |

`mise run status` shows all of these in one view.

## Consequences

- There is no `STATUS.md`, `WORKLOG.md`, or `ESCALATE.md`.
- The PR template replaces the worklog.
- The issue template replaces the task description in a status file.
- Without a GitHub remote, `mise run status` shows only the git part.
