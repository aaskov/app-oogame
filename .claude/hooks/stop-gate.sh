#!/usr/bin/env bash
# Stop hook. The agent cannot report done while the gate fails.
# Exit 2 blocks the stop. Claude Code shows stderr to the agent.
#
# On the second stop attempt (stop_hook_active), the hook lets the agent stop.
# This prevents a loop. CI and the pre-commit hook still run the gate.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=.mise/lib/common.sh
source "$here/../../.mise/lib/common.sh"
export SEED_ROOT="${SEED_ROOT:-${CLAUDE_PROJECT_DIR:-$(cd "$here/../.." && pwd)}}"

if [ "$(jq -r '.stop_hook_active // false')" = "true" ]; then
  exit 0
fi

cd "$SEED_ROOT"

# Skip the gate when nothing changed: a clean tree and no commits ahead of base.
ahead="$(git rev-list --count "$(seed_base_ref)..HEAD" 2>/dev/null || echo 1)"
if [ -z "$(git status --porcelain)" ] && [ "$ahead" = "0" ]; then
  exit 0
fi

if ! output="$(bash -c "${SEED_GATE_CMD:-mise run check}" 2>&1)"; then
  echo "The gate failed. 'mise run check' must pass before you report done (AGENTS.md, R1)." >&2
  printf '%s\n' "$output" | tail -n 40 >&2
  exit 2
fi
