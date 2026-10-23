# 0006 — Start and finish an agent with one command

**Status:** Accepted · 2026-10-19

## Context

Without help, the architect starts each agent by hand: clone, branch,
container, Claude, `/login`, prompt. After the merge, the architect checks and
removes each clone by hand. A git worktree does not work, because its `.git`
file points to a host path that the container does not have. The first app
used these tasks for two features (auth and planets) before they moved here.

## Decision

- **`mise run agent:start <issue>`** (host, from the main checkout):
  1. It reads the open issue and makes a slug from its title.
  2. It clones `origin` into `../<repo>-agent-<issue>`.
  3. It creates the branch `agent/<issue>-<slug>`.
  4. It runs `devcontainer up`.
  5. It starts Claude Code in the container with the issue prompt.
- **`mise run agent:finish <issue>`** (host): it refuses if the clone has
  uncommitted changes, or commits that are not in a PR. Otherwise it removes
  the containers (with a compose project, also its volumes), then the clone.
- **No `/login` in each container:** `claude setup-token` makes a long-lived
  token on the host, in `~/.config/claude-agent/oauth-token`. The container
  mounts the folder read-only. `.devcontainer/claude-auth.sh` puts a wrapper
  in front of `claude` that sets `CLAUDE_CODE_OAUTH_TOKEN` from the file.
- **The model:** an agent uses `claude-sonnet-5-5`. `AGENT_MODEL=<model>`
  overrides it for one start. The seed sets no model in `.claude/settings.json`,
  so a session in the main checkout (the architect) keeps the Claude default.
- **The permission mode:** an agent runs in `auto` mode, so it does not ask
  before each command. `AGENT_PERMISSION_MODE=<mode>` overrides it for one
  start, for example `default`. The guard hook, the Stop gate, `check:guarded`,
  and the rulesets stay active in each mode. The seed sets no mode in
  `.claude/settings.json`, so an architect session keeps its own mode.
- `AGENT_START_NO_CLAUDE=1` prints the model, the mode, and the prompt in place of starting Claude.

## Consequences

- An agent starts with one command and is removed with one command.
- An agent in the container can read the Claude token, as it can read the bot
  key (ADR 0005). The token gives Claude Code access with the architect's
  subscription. Revoke it in the Claude account settings if it leaks.
- An app with published ports or a database must give each clone its own
  ports and volumes. The seed has neither, so that part belongs to the app.
