# Shared functions for the checks and the Claude Code hooks.
# Source this file. Do not run it.
#
# Overrides for tests:
#   SEED_ROOT      repository root (default: git toplevel)
#   SEED_BRANCH    branch name (default: current branch)
#   SEED_BASE_REF  base ref for diffs (default: main)

seed_root() {
  if [ -n "${SEED_ROOT:-}" ]; then
    printf '%s\n' "$SEED_ROOT"
  else
    git rev-parse --show-toplevel
  fi
}

seed_branch() {
  if [ -n "${SEED_BRANCH:-}" ]; then
    printf '%s\n' "$SEED_BRANCH"
  else
    git -C "$(seed_root)" branch --show-current
  fi
}

seed_base_ref() {
  printf '%s\n' "${SEED_BASE_REF:-main}"
}

# Print the guarded patterns from CODEOWNERS, one for each line.
guarded_patterns() {
  local codeowners
  codeowners="$(seed_root)/.github/CODEOWNERS"
  [ -f "$codeowners" ] || return 0
  awk '$1 ~ /^\// { print $1 }' "$codeowners"
}

# Return 0 if the repo-relative path is guarded.
is_guarded() {
  local path="/${1#/}" pattern
  while IFS= read -r pattern; do
    case "$pattern" in
      */) [[ "$path" == "$pattern"* ]] && return 0 ;;
      *)  [[ "$path" == "$pattern" ]] && return 0 ;;
    esac
  done < <(guarded_patterns)
  return 1
}
