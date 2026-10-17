# 0003 — No rule without a check

**Status:** Accepted · 2026-10-15

## Context

A rule in prose is a request to the agent. Agents break such rules when
the rule conflicts with the task. The architect then finds the break in
review, or does not find it.

## Decision

Each rule in `AGENTS.md` names the `mise` task that enforces it.
`check:rules` fails if a named task does not exist. A rule that no
machine can check is not a rule. Write it as guidance under "Procedure",
or delete it.

The gate is `mise run check`. It runs in three places:

1. The Claude Code `Stop` hook, before the agent reports done.
2. The git `pre-commit` hook.
3. CI, on each pull request and each push to `main`.

The guardrails protect themselves:

- `.github/CODEOWNERS` lists the guarded paths. It is the single source.
- The `PreToolUse` hook blocks agent edits to guarded paths.
- `check:guarded` fails if an `agent/` branch changes a guarded path.
  This catches writes through Bash, which the hook does not see.
- `tests/guardrails/` holds one seeded violation for each guardrail.
  `check:guardrails` proves that each guardrail fails on its seed.

## Consequences

- `AGENTS.md` stays short. `check:rules` limits it to 60 lines.
- Known limit: agents run with the architect's git and GitHub identity.
  An agent can create an `architect/` branch or approve its own PR as the
  owner. A separate identity for agents (a bot account or a GitHub App)
  closes this gap. This is an open decision.
