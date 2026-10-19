# 0109 — Planets and vaults: a user owns planets, each planet has one vault

**Status:** Accepted · 2026-10-19

## Context

A user has one or more planets. Each planet has a vault with three resources:
metal, crystal, and deuterium. A logged-in user must list their planets, read
the vault of a planet, and set new values in it. A user must never read or
change the planet or the vault of a different user.

## Decision

- **One module, `planets`,** owns both tables. A vault cannot exist without
  its planet, so they belong together.
- **Tables:**
  - `planets`: `id`, `user_id` (foreign key to `users.id`), `name`, `is_home`.
    A partial unique index allows at most one home planet for each user.
  - `vaults`: `planet_id` is the primary key and a foreign key to `planets.id`.
    So each planet has at most one vault. `BIGINT` columns with a `CHECK >= 0`.
- **Operations:**
  - `GET /planets` lists the planets of the user.
  - `GET /planets/{planet_id}/vault` and `PATCH /planets/{planet_id}/vault`.
- **Ownership:** the service loads a planet only with both its ID and the user
  ID. If the planet does not exist, or it belongs to a different user, the
  response is the same 404. So the response does not tell an attacker which
  planet IDs exist.
- **Who is the user:** `auth.public_api.get_current_user_id` is a `Depends()`
  provider. It returns only the user ID, because the auth `User` holds the
  password hash. Never take a user ID from the URL or the body.
- **The home planet:** if the user has no planets, the first `GET /planets`
  creates "Homeworld" with `is_home = true` and its vault with the start
  values metal 500, crystal 500, deuterium 0 (`app.shared.orm`). The planet
  and the vault are created in one transaction. The auth module does not
  change. Two first requests at the same time must not fail and must not
  create two home planets. The repository uses
  `INSERT ... ON CONFLICT DO NOTHING` on the partial unique index.
- **Update:** `PATCH` replaces each value that is in the body. The others do
  not change. The contract limits each amount to 0 to 2^53 − 1, the largest
  integer that JavaScript holds without a loss of precision. The last write wins.
- **No coordinates yet.** A planet has only a name. Coordinates belong to a
  later galaxy feature.

## Consequences

- The tables allow many planets, but no operation creates a second planet
  yet. A later feature, for example colonization, adds that.
- Each user can give themselves any amount. That is a cheat in a game. It is
  acceptable until a later feature, for example mines, produces the resources.
- A `GET /planets` can write rows. That is the price of not changing the auth module.
