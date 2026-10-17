# app-oogame

Ogame clone

Agents write the code and machines check it. The architect reviews only
contracts and decisions. This repository comes from
[agentic-seed](/private/var/folders/9p/1bj8950n47qc7b6x9f8s79b80000gp/T/copier._vcs.clone.m29tkl5r).

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

## Add a stack

The gate has five empty slots in `.mise/tasks/check/`: `lint`, `types`,
`test`, `boundaries`, and `contracts`. To add a stack:

1. Add the tools to `[tools]` in `mise.toml`.
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
