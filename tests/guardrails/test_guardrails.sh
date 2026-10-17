#!/usr/bin/env bash
# Seeded violations. Each case proves that a guardrail fails when it must,
# and passes when it must. If a guardrail stops working, this test fails.
set -uo pipefail

# shellcheck source=tests/guardrails/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

# A scratch repository with the real CODEOWNERS, so the tests do not touch this repo.
scratch="$tmp/scratch"
gitc() { git -C "$scratch" -c user.name=seed -c user.email=seed@example.invalid -c commit.gpgsign=false "$@"; }
git init -q -b main "$scratch"
mkdir -p "$scratch/.github"
cp "$repo/.github/CODEOWNERS" "$scratch/.github/CODEOWNERS"
gitc add . && gitc commit -q -m init

# --- guard-paths hook ---------------------------------------------------------

# The hook depends on the branch. The cases pin it, so the result does not
# depend on the branch that runs the gate.
guard() {
  printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$1" |
    SEED_ROOT="$repo" SEED_BRANCH="${2:-agent/1-feature}" "$hooks/guard-paths.sh"
}
guard_notebook() {
  printf '{"tool_name":"NotebookEdit","tool_input":{"notebook_path":"%s"}}' "$1" |
    SEED_ROOT="$repo" SEED_BRANCH=agent/1-feature "$hooks/guard-paths.sh"
}

expect 2 "hook blocks an edit in contracts/" guard "$repo/contracts/api.yaml"
expect 2 "hook blocks an edit to CLAUDE.md" guard "$repo/CLAUDE.md"
expect 2 "hook blocks an edit to a check" guard "$repo/.mise/tasks/check/lint"
expect 2 "hook blocks a relative guarded path" guard "mise.toml"
expect 2 "hook blocks a notebook in docs/adr/" guard_notebook "$repo/docs/adr/x.ipynb"
expect 2 "hook blocks a guarded edit on main" guard "$repo/mise.toml" main
expect 2 "hook blocks a guarded edit on a detached HEAD" guard "$repo/mise.toml" ""
expect 0 "hook allows a guarded edit on an architect branch" guard "$repo/mise.toml" architect/stack
expect 0 "hook allows an edit in src/" guard "$repo/src/app.py"
expect 0 "hook allows docs outside docs/adr/" guard "$repo/docs/notes.md"
expect 0 "hook allows a path outside the repo" guard "/tmp/other/mise.toml"

# --- check:rules --------------------------------------------------------------

# shellcheck disable=SC2016 # The backticks are literal Markdown.
printf '| R1 | Do a thing. | `check:does-not-exist` |\n' >"$tmp/unknown-check.md"
printf '# No rules here\n' >"$tmp/no-rules.md"

expect 0 "check:rules passes on AGENTS.md" "$checks/rules"
expect 1 "check:rules fails when a rule names a missing check" \
  env SEED_AGENTS_FILE="$tmp/unknown-check.md" "$checks/rules"
expect 1 "check:rules fails when there are no rule rows" \
  env SEED_AGENTS_FILE="$tmp/no-rules.md" "$checks/rules"
expect 1 "check:rules fails when AGENTS.md is too long" \
  env SEED_AGENTS_MAX_LINES=5 "$checks/rules"

# --- check:branch -------------------------------------------------------------

expect 0 "check:branch allows main" env SEED_BRANCH=main "$checks/branch"
expect 0 "check:branch allows agent/<issue>-<slug>" env SEED_BRANCH=agent/12-add-login "$checks/branch"
expect 0 "check:branch allows architect/<slug>" env SEED_BRANCH=architect/seed-v2 "$checks/branch"
expect 1 "check:branch fails on feature/<slug>" env SEED_BRANCH=feature/login "$checks/branch"
expect 1 "check:branch fails without an issue number" env SEED_BRANCH=agent/login "$checks/branch"

# --- check:guarded ------------------------------------------------------------

guarded() { SEED_ROOT="$scratch" SEED_BRANCH="$1" "$checks/guarded"; }

gitc checkout -q -b agent/1-feature
mkdir -p "$scratch/src" && echo "x" >"$scratch/src/app.py"
expect 0 "check:guarded allows an agent change in src/" guarded agent/1-feature

mkdir -p "$scratch/contracts" && echo "x" >"$scratch/contracts/api.yaml"
expect 1 "check:guarded fails on an untracked file in contracts/" guarded agent/1-feature
expect 0 "check:guarded allows the change on an architect branch" guarded architect/contracts

gitc add . && gitc commit -q -m "change contracts"
expect 1 "check:guarded fails on a committed change in contracts/" guarded agent/1-feature

# --- stop-gate hook -----------------------------------------------------------

stop() {
  printf '{"stop_hook_active":%s}' "$1" |
    SEED_ROOT="$scratch" SEED_GATE_CMD="$2" "$hooks/stop-gate.sh"
}

expect 2 "stop hook blocks when the gate fails" stop false false
expect 0 "stop hook allows a stop when the gate passes" stop false true
expect 0 "stop hook allows the second stop attempt" stop true false

gitc checkout -q main
expect 0 "stop hook skips the gate when nothing changed" stop false false

# --- result -------------------------------------------------------------------

guardrails_result guardrails
