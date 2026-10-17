# Shared helper for the guardrail tests. Source it from a test_*.sh file.
# It gives: $repo, $checks, $hooks, $tmp, expect, and guardrails_result.

# The cases set their own overrides. Overrides from the caller, such as CI,
# must not leak into the cases.
unset SEED_ROOT SEED_BRANCH SEED_BASE_REF SEED_GATE_CMD SEED_AGENTS_FILE SEED_AGENTS_MAX_LINES

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
checks="$repo/.mise/tasks/check"
hooks="$repo/.claude/hooks"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cd "$repo" || exit 1

passed=0
failed=0

# expect <exit code> <description> <command...>
expect() {
  local want="$1" name="$2" got=0
  shift 2
  "$@" >"$tmp/out" 2>&1 || got=$?
  if [ "$got" = "$want" ]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    echo "FAIL: $name (expected exit $want, got $got)"
    sed 's/^/  | /' "$tmp/out"
  fi
}

# guardrails_result <name>: print the totals and fail if a case failed.
guardrails_result() {
  echo "$1: $passed passed, $failed failed"
  [ "$failed" = 0 ]
}
