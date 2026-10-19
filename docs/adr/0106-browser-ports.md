# 0106 — Browser access for the main checkout

**Status:** Accepted · 2026-10-19

## Context

ADR 0103 published no host ports, so parallel agent clones do not clash.
Then the architect cannot try the app in a browser.

## Decision

- The `dev` service publishes ports 8000 (backend) and 3000 (frontend) on
  `127.0.0.1` only. Nothing is open to the network.
- `.devcontainer/initialize.sh` runs on the host before each start and writes
  `.devcontainer/.env` (ignored by git):
  - **Main checkout:** host ports 8000 and 3000.
  - **Agent clone** (a folder named `*-agent-*`): host port 0. Docker picks a
    free port, so clones never clash.
- `mise run serve:backend` (uvicorn with reload) and `mise run serve:frontend`
  (next dev) start the servers in the container on `0.0.0.0`.
- The URLs match the defaults: `NEXT_PUBLIC_API_URL` is `http://localhost:8000`,
  and `CORS_ORIGINS` allows `http://localhost:3000`. The session cookie works,
  because both are the same site (`localhost`).

## Consequences

- Only one main checkout at a time can use ports 8000 and 3000.
- An agent clone must use the name pattern `*-agent-*`. `mise run start` (later)
  will create clones with that name.
- `docker compose port dev 8000` shows the random port of a clone, if needed.
