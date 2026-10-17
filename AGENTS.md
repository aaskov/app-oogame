# AGENTS.md

Rules for each agent in this repository. `CLAUDE.md` is a link to this file.

## Rules

A machine enforces each rule in this table. The check column names the
`mise` task that enforces the rule. `check:rules` makes sure that each
check exists.

| ID | Rule | Check |
|----|------|-------|
| R1 | Before you report a task as done, `mise run check` must pass. | `check` |
| R2 | Do not change a guarded path. `.github/CODEOWNERS` lists the guarded paths. | `check:guarded` |
| R3 | Use one branch for each issue. Name it `agent/<issue>-<slug>`. | `check:branch` |

## Procedure

1. Read the issue. The acceptance criteria are the scope.
2. Create the branch `agent/<issue>-<slug>`.
3. Run `mise run check` until it passes.
4. Open a PR. Fill in the PR template. The PR description is the worklog.

## When you are blocked

Stop. Do not work around a check. Write a comment on the issue in this
format, then add the label `needs-decision`:

`blocked on · options considered · recommendation`

## Commands

| Command | Use |
|---------|-----|
| `mise run check` | Run the gate. |
| `mise run status` | Show the project state. |
| `mise run setup` | Install the git hooks. Run it once for each clone. |

## Where things are

- `contracts/` — interfaces between the parts of the app. Guarded.
- `docs/adr/` — architecture decisions. Guarded.
- `.mise/tasks/check/` — the checks of the gate. Guarded.
