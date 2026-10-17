# 0005 — Agents use a bot identity

**Status:** Accepted · 2026-10-17

## Context

ADR 0003 names a known limit: agents use the git and GitHub identity of
the architect. Then GitHub cannot tell an agent from the architect. An
agent can push to `main`, create an `architect/` branch, or approve its
own PR as the code owner.

## Decision

Agents act as a GitHub App (the agent bot), not as the architect.

- The private key stays on the host, in `~/.config/agent-bot/`. The
  devcontainer mounts that folder read-only at `/mnt/agent-bot`.
- `.devcontainer/agent-bot/token.sh` gets an installation token. The token
  is scoped to this repository and is valid for one hour.
- In the devcontainer, git pushes over HTTPS with the token, and `gh` uses
  the token. Commits have the bot as the author.
- The App has write access to contents, pull requests, and issues only.
  It has no access to workflows or administration.
- GitHub rulesets hold the hard limits. The bot has no bypass:
  - `main` needs a PR, one approval from the code owner, and a green `check`.
  - Only the architect can create or push `architect/**` branches.

## Consequences

- The architect works on the host. The devcontainer is the agent environment.
- If the key or the app ID is missing, the bot is off. This is the case in CI.
- An agent in the container can read the key. With the key, it can get
  tokens with the bot permissions on the installed repositories only.
  The key must stay out of each repository and out of each log.
- Rulesets on a private repository need GitHub Pro or a public repository.
