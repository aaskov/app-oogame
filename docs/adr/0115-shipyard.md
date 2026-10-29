# 0115 — Shipyard: two ships, one order at a time, completed on read

**Status:** Accepted · 2026-10-26

## Context

The planet has mines, energy, storage, and build time (ADR 0111 to 0114).
In OGame, a shipyard builds ships. Ships are the base for fleets later.

## Decision

- **An eighth building kind, `shipyard`.** It uses the `buildings` table. A
  migration adds it to the check constraint `known_kind` of `buildings` and
  `constructions`. The buildings list has eight buildings, with `shipyard`
  last. The upgrade follows ADR 0114. The shipyard uses no energy and
  produces nothing.
- **Upgrade cost of the shipyard** from level L to L+1:
  `400 · 2^L` metal, `200 · 2^L` crystal, `100 · 2^L` deuterium.
- **Two ship kinds**, cost of one ship:

  | Ship | Metal | Crystal | Deuterium |
  |---|---|---|---|
  | `small_cargo` | 2000 | 2000 | 0 |
  | `light_fighter` | 3000 | 1000 | 0 |

  The table `ships` has `planet_id`, `kind`, and `count`. No row means 0.
- **Build time of one ship** in seconds, rounded down, at least 1, at
  shipyard level S:
  `3600 · (metal cost + crystal cost) / 2500 / (1 + S) / GAME_SPEED`.
  A small cargo at shipyard level 1 takes 2880 seconds at speed 1.
- **One running ship order for each planet.** The table `ship_orders` has
  `planet_id` (the primary key), `kind`, `remaining`, `seconds_per_ship`,
  and `next_finishes_at`. No row means no running order. The order is
  separate from the building upgrade, so both can run at the same time.
- **Start of an order** (`order_ships`, count from 1 to 1000), in one
  transaction with the vault lock of ADR 0111:
  1. Complete the ships that are due (see below).
  2. If the shipyard has level 0: 409, and nothing changes.
  3. If an order still runs: 409, and nothing changes.
  4. Store the amounts up to now. Check the cost of all the ships. If the
     vault has too little: 409, and nothing changes.
  5. Subtract the cost. Add the row with `remaining = count`,
     `seconds_per_ship` at the shipyard level of now, and
     `next_finishes_at = now + seconds_per_ship`.
  The player pays at the start. There is no cancel. A later shipyard upgrade
  does not change the time of a running order.
- **Completion on read.** Each read of the shipyard and each order start
  first completes the ships that are due, under the vault lock:
  1. If `next_finishes_at` is after now, nothing is due.
  2. Else `done = min(remaining, 1 + floor((now − next_finishes_at) / seconds_per_ship))`.
  3. Add `done` to the count of the kind.
  4. If `done = remaining`, delete the order. Else subtract `done` from
     `remaining`, and add `done · seconds_per_ship` to `next_finishes_at`.
  There is no background job. Ships do not change the vault.
- **The answer.** `Shipyard` has the two ships, in the order `small_cargo`,
  `light_fighter`. It has `order` only if an order runs (no `null`).
  `order.finishes_at = next_finishes_at + (remaining − 1) · seconds_per_ship`.
  The 409 `detail` tells which reason applies.

## Consequences

- `list_buildings` and `upgrade_building` are `x-planned` in the prep,
  because `BuildingKind` gets `shipyard`. `read_shipyard` and `order_ships`
  are new and `x-planned`. The cleanup removes the flags (done after #63
  and #64).
- The prep adds the label of the shipyard to the frontend, so that the type
  check passes. The new schemas are exported in `frontend/src/lib/api.ts`
  (lesson 17).
- Ships have no use yet. Fleets and missions are a later feature.
