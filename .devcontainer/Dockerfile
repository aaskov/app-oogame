FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG MISE_VERSION=v2026.9.12

RUN apt-get update \
 && apt-get install -y --no-install-recommends jq \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://mise.run | MISE_VERSION="${MISE_VERSION}" MISE_INSTALL_PATH=/usr/local/bin/mise sh
