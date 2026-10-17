# 0002 — One devcontainer for each repository

**Status:** Accepted · 2026-10-15

## Context

An app often has a backend and a frontend. One option is a devcontainer
for each app folder. That option is good for a human who opens one folder
in an IDE. It is bad for an agent:

- An agent task often crosses the folders. A contract change touches
  `contracts/`, the backend, and the frontend in one PR.
- The gate must run in one place. `mise run check` needs every toolchain.
  A backend container cannot run the frontend checks.
- CI must run the same environment as the agents. One container gives
  one CI job. Two containers give two jobs and a gap between them.
- Worktrees multiply the containers. With N worktrees and M app folders,
  you get N × M containers, port sets, and network names.
- The agent runs in one environment. Its hooks run `mise run check`
  there. That environment must have all the tools.

## Decision

The repository has one devcontainer, at the root. It holds the tools for
all the apps. Each tool version is pinned in `mise.toml`.

Two different things must stay separate:

- **Development environment:** one devcontainer, for agents, humans, and CI.
- **Runtime images:** one Dockerfile for each deployable app. These are
  for deployment, not for development.

When the apps need services, such as a database, the devcontainer uses
`dockerComposeFile`. The services run as sidecars next to the one
development container.

## Consequences

- The image is larger, because it holds all the toolchains.
- One worktree uses one container. That is N containers for N worktrees.
- A per-app devcontainer is correct only in these cases. Write a new ADR
  if one of them occurs:
  - The toolchains conflict and cannot be installed together.
  - The image build time becomes a real problem.
  - The apps have separate teams and separate release cycles. Then the
    apps are better as separate repositories.
