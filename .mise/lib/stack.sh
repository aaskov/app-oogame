# Shared functions for the stack slots (docs/adr/0100). Source this file.
#
# The tools come from the real repository: backend/.venv and frontend/node_modules.
# The target comes from SEED_ROOT, so the guardrail tests can check a copy.
# shellcheck source=.mise/lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

stack_tools="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
stack_target="$(seed_root)"

# py <tool> [args...]: run a tool from backend/.venv.
py() {
  local tool="$1"
  shift
  "$stack_tools/backend/.venv/bin/$tool" "$@"
}

# has_backend: return 0 if the target has a backend.
has_backend() { [ -f "$stack_target/backend/pyproject.toml" ]; }
