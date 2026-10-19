# app-oogame

Ogame clone

Agents write the code and machines check it. The architect reviews only
contracts and decisions. This repository comes from
[agentic-seed](https://github.com/aaskov/agentic-seed).

## Start

1. Open the repository in its devcontainer.
2. Run `mise run status` to see the project state.
3. Run `mise run check` to run the gate.

## The parts

| Part | File |
|------|------|
| Rules for agents | `AGENTS.md` |
| Commands | `mise.toml` and `.mise/tasks/` |
| The gate | `mise run check` |
| Review surface | `contracts/` and `docs/adr/` |
| Guarded paths | `.github/CODEOWNERS` |
| Guardrail tests | `tests/guardrails/` |

## Agent identity

Agents act as a GitHub App, not as you (docs/adr/0005). To turn it on:

1. Create a GitHub App with write access to contents, pull requests, and issues.
2. Install it on this repository only.
3. Put its private key at `~/.config/agent-bot/private-key.pem` on the host.
4. Set the app ID and name in `.devcontainer/agent-bot.env`.

Then rebuild the devcontainer.

## Add a stack

The gate has five empty slots in `.mise/tasks/check/`: `lint`, `types`,
`test`, `boundaries`, and `contracts`. To add a stack:

1. Add the tools to `[tools]` in `mise.container.toml`. Only the devcontainer loads that file.
2. Replace each slot file with a script that runs the tool.
3. Add the stack manifests, such as `pyproject.toml`, to `.github/CODEOWNERS`.

## Update from the seed

The architect runs this on the host, on an `architect/` branch:

```bash
uvx copier update
```

Copier merges the new seed version into this repository. Then review the
diff and open a PR.

## Decisions

See `docs/adr/`. Start with 0002 and 0003.
