#!/usr/bin/env bash
# Git credential helper. It gives git the agent bot token for github.com.
set -euo pipefail
[ "${1:-}" = get ] || exit 0
cat >/dev/null
echo "username=x-access-token"
echo "password=$("$(dirname "${BASH_SOURCE[0]}")/token.sh")"
