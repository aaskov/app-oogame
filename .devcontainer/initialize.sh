#!/usr/bin/env bash
# Runs on the host before each devcontainer start (docs/adr/0106).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# The bind mount of the bot key needs the folder to exist, also on CI runners without a key.
mkdir -p "$HOME/.config/agent-bot" "$HOME/.config/claude-agent"

# Host ports for the dev servers. Compose reads .env in this folder.
# The main checkout gets fixed ports for the browser. An agent clone
# (a folder named *-agent-*) gets port 0: Docker picks a free port, so
# clones never clash.
case "$(basename "$(cd .. && pwd)")" in
  *-agent-*) backend=0 frontend=0 ;;
  *) backend=8000 frontend=3000 ;;
esac
printf 'BACKEND_HOST_PORT=%s\nFRONTEND_HOST_PORT=%s\n' "$backend" "$frontend" >.env
