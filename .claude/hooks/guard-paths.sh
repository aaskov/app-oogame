#!/usr/bin/env bash
# PreToolUse hook. It blocks agent edits to guarded paths (.github/CODEOWNERS).
# Exit 2 blocks the tool call. Claude Code shows stderr to the agent.
#
# On an architect/ branch, the hook allows the edit, the same as check:guarded.
# This lets the architect use Claude for guarded changes. An agent can create
# an architect/ branch locally, but the GitHub ruleset rejects its push.
#
# Limit: this hook sees only the Edit, Write, and NotebookEdit tools. A write
# through Bash passes here. check:guarded catches that write in the gate.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=.mise/lib/common.sh
source "$here/../../.mise/lib/common.sh"
export SEED_ROOT="${SEED_ROOT:-${CLAUDE_PROJECT_DIR:-$(cd "$here/../.." && pwd)}}"

if [[ "$(seed_branch)" == architect/* ]]; then
  exit 0
fi

file="$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty')"
[ -n "$file" ] || exit 0

case "$file" in
  "$SEED_ROOT"/*) rel="${file#"$SEED_ROOT"/}" ;;
  /*) exit 0 ;;  # Outside the repository.
  *) rel="$file" ;;
esac

if is_guarded "$rel"; then
  echo "Blocked: '$rel' is a guarded path (.github/CODEOWNERS). Do not change it." >&2
  echo "If the task needs this change, follow 'When you are blocked' in AGENTS.md." >&2
  exit 2
fi
