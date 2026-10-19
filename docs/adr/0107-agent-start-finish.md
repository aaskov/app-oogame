# 0107 — Start and finish an agent with one command

**Status:** Accepted · 2026-10-19 · Superseded in part by seed ADR 0006 (seed v0.3.0)

The tasks and the Claude token now come from the seed (`docs/adr/0006`). This
app keeps the part that the seed does not have: random host ports for each
clone (ADR 0106) and a database volume for each clone, in `compose.yml`.

## Context

In the first agent run (auth, #12 and #13), the architect started each agent
by hand: clone, branch, container, Claude, `/login`, prompt. After the merge,
the architect checked and removed each clone by hand. A git worktree does not
work, because its `.git` file points to a host path that the container does
not have.

## Decision

- **`mise run agent:start <issue>`** (host, from the main checkout):
  1. It reads the open issue and makes a slug from its title.
  2. It clones `origin` into `../<repo>-agent-<issue>`. That name gives the
     clone random host ports (ADR 0106).
  3. It creates the branch `agent/<issue>-<slug>`.
  4. It runs `devcontainer up`.
  5. It starts Claude Code in the container with the issue prompt.
- **`mise run agent:finish <issue>`** (host): it refuses if the clone has
  uncommitted changes, or commits that are not in a PR. Otherwise it removes
  the compose project with its database volume, then the clone.
- **No `/login` in each container:** `claude setup-token` makes a long-lived
  token on the host, in `~/.config/claude-agent/oauth-token`. The container
  mounts the folder read-only. `.devcontainer/claude-auth.sh` puts a wrapper
  in front of `claude` that sets `CLAUDE_CODE_OAUTH_TOKEN` from the file.
- `AGENT_START_NO_CLAUDE=1` prints the prompt in place of starting Claude.

## Consequences

- An agent starts with one command and is removed with one command.
- An agent in the container can read the Claude token, as it can read the bot
  key (seed ADR 0005). The token gives Claude Code access with the architect's
  subscription. Revoke it in the Claude account settings if it leaks.
- These tasks are in the app first. They move to the seed when they work for
  a second feature.
