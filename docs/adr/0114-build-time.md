# 0114 — Build time: one upgrade at a time, completed on read

**Status:** Accepted · 2026-10-23

## Context

Since ADR 0111, an upgrade is instant. In OGame, an upgrade takes time, and a
planet builds one building at a time.

## Decision

- **One running upgrade for each planet.** The table `constructions` has
  `planet_id` (the primary key), `kind`, and `finishes_at`. No row means no
  running upgrade.
- **Build time** in seconds, rounded down, at least 1:
  `3600 · (metal cost + crystal cost) / 2500 / GAME_SPEED`.
  Metal mine level 0 to 1 costs 60 + 15, so it takes 108 seconds at speed 1.
- **Start of an upgrade** (`upgrade_building`), in one transaction with the
  vault lock of ADR 0111:
  1. Complete an upgrade that is due (see below).
  2. If an upgrade still runs: 409, and nothing changes.
  3. Store the amounts up to now. Check the cost. If the vault has too
     little: 409, and nothing changes.
  4. Subtract the cost, and add the row with `finishes_at = now + build time`.
     The level does not change yet.
  The player pays at the start. There is no cancel.
- **Completion on read.** An upgrade with `finishes_at` at or before now is
  due. Each read of the vault or the buildings, and each upgrade start,
  first completes it, under the vault lock:
  1. Store the amounts up to `finishes_at`, with the old levels.
  2. Raise the level, and delete the row.
  Then the read calculates from `finishes_at` to now with the new levels. So
  the old level counts before `finishes_at`, and the new level counts after
  it. The calculation stays exact, and there is no background job. A stored
  time never goes back (ADR 0111): the amounts are stored at
  `max(finishes_at, updated_at)`.
- **The answer.** A `Building` with a running upgrade has
  `upgrade_finishes_at`. Other buildings do not have the field (no `null`).
  `upgrade_building` returns the building with the old level and
  `upgrade_finishes_at`. The 409 `detail` tells which reason applies.

## Consequences

- `list_buildings` and `upgrade_building` are `x-planned` in the prep, because
  their responses changed. The cleanup removes the flags.
- A read of the vault or the buildings can write. It takes the vault lock only
  when an upgrade is due.
- No new schema, so `frontend/src/lib/api.ts` needs no new export (lesson 17).
