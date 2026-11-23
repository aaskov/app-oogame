# 0118 — Galaxy: coordinates for each planet, a username, and a system view

**Status:** Accepted · 2026-11-23

## Context

A planet has no place in the universe yet, and a player sees only their own
planets. Fleets (a later feature) need coordinates. The galaxy view shows the
other players, so a player needs a public name. The email must never be
public.

## Decision

- **The universe:** `galaxies` galaxies, `systems_per_galaxy` systems in each
  galaxy, and 15 positions in each system. The defaults are 1 and 50. They are
  settings (`GALAXIES`, `SYSTEMS_PER_GALAXY`), so the universe can grow later.
- **Coordinates:** each planet has `galaxy`, `system`, and `position`. The
  unique constraint `uq_planets_coordinates` allows one planet for each
  position. The frontend shows them as `[galaxy:system:position]`, for
  example `[1:23:7]`.
- **The home planet** gets a random free position from 4 to 12, in a random
  system of a random galaxy. If the insert hits the unique constraint
  because another request took the position, the backend tries another
  free position. If no position from 4 to 12 is free, `list_planets`
  returns 503. The migration gives each existing planet a position by the
  same rule.
- **Username:** the player chooses it at registration. It has 3 to 20
  characters from `A-Z`, `a-z`, `0-9`, `_`, and `-`. It is unique, and the
  case counts. A used username gives 409 with a `detail` that is different
  from the "email exists" detail. The migration gives each existing user
  `player-<number>`, in the order of registration. `User` has `username`.
- **The galaxy view** (`read_galaxy_system`,
  `GET /galaxy/{galaxy}/{system}`) returns the 15 positions of one system.
  A position with a planet has the planet name and the username of the
  owner. It never has an email, an amount, a level, or a planet ID. Each
  logged-in player can see each system. A galaxy or a system larger than the
  universe gives 404.
- **The frontend:** a Galaxy page, `/galaxy/[galaxy]/[system]`, with a link in
  the top bar. It has buttons for the previous and the next system. The link
  opens the system of the home planet first. The planet pages show the
  coordinates of the planet.

## The change in two steps

The columns `galaxy`, `system`, `position`, and `username` are nullable in
the prep migration. So the code of today, which does not set them, keeps
working. `Registration.username` is optional in the contract for the same
reason: the register form of today does not send it.

1. **Expand (the prep).** Nullable columns, the backfill, and the contract
   with `x-planned` on `register`, `login`, `read_me`, `list_planets`, and
   `read_galaxy_system`. The backend issue sets the values for each new row
   and requires the username. The frontend issue sends it.
2. **Contract (the cleanup).** A migration makes the four columns
   `NOT NULL`. The contract makes `Registration.username` required and
   removes the flags.

## Consequences

- `register`, `login`, and `read_me` change in the auth module, and
  `list_planets` and `read_galaxy_system` are in the planets module. The
  planets repository reads the usernames with a join on `UserRow` from
  `app/shared/orm/`, so no `public_api.py` changes.
- Two guardrail cases of `check:contracts` used auth operations. An
  operation that is `x-planned` skips the schema compare, so the cases now
  use the ship operations.
- The new schemas are exported in `frontend/src/lib/api.ts` (lesson 17).
