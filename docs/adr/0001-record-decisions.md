# 0001 — Record architecture decisions

**Status:** Accepted · 2026-10-15

## Context

Agents do not remember earlier sessions. A decision that is not written
down gets made again, often in a different way.

## Decision

We record each architecture decision as one file in `docs/adr/`.
The file name is `NNNN-short-title.md`. Each file has these sections:
Status, Context, Decision, Consequences.

An accepted ADR does not change. To change a decision, write a new ADR
that supersedes the old one, and set the old status to "Superseded by NNNN".

## Consequences

- An agent can read why the repository is the way it is.
- `docs/adr/` is guarded. Only the architect writes ADRs. An agent
  proposes a decision with the `needs-decision` label on its issue.
