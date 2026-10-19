#!/usr/bin/env bash
# Runs once, after the container is created.
set -euo pipefail
git config --global --add safe.directory "$PWD"
mise trust --yes mise.toml
mise trust --yes mise.container.toml
mise install
mise run setup
.devcontainer/agent-bot/setup.sh
