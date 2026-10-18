FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG MISE_VERSION=v2026.9.12

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl jq openssl \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://mise.run | MISE_VERSION="${MISE_VERSION}" MISE_INSTALL_PATH=/usr/local/bin/mise sh

# The tools pinned in mise.toml come first on PATH, also for a plain shell.
# An agent runs plain shell commands. Without this, it finds other versions,
# for example the Node that the Claude Code feature installs.
ENV PATH="/home/vscode/.local/share/mise/shims:${PATH}"
