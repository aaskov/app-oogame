# 0113 — Storage: a maximum for each resource

**Status:** Accepted · 2026-10-23

## Context

Since ADR 0111, the amounts grow without a limit. In OGame, each resource has
a maximum, and a storage building raises it.

## Decision

- **Three new building kinds:** `metal_storage`, `crystal_storage`, and
  `deuterium_tank`. They use the `buildings` table. A migration adds them to
  the check constraint `known_kind`. The buildings list has seven buildings,
  in the order `metal_mine`, `crystal_mine`, `deuterium_synthesizer`,
  `solar_plant`, `metal_storage`, `crystal_storage`, `deuterium_tank`.
- **Capacity** of a resource, at storage level L:
  `5000 · floor(2.5 · e^(20 · L / 33))`. At level 0, that is 10,000. Level 1
  gives 20,000. Level 2 gives 40,000. `GAME_SPEED` does not change it.
- **Production stops at the capacity.** For each resource, a read returns:
  - the stored amount, if the stored amount is at or above the capacity;
  - else `min(capacity, floor(stored + production_per_hour × hours))`.

  An amount above the capacity stays, but it does not grow. The result is at
  most 2^53 − 1, as in ADR 0111.
- **The calculation stays exact on read.** The capacity changes only when a
  building gets a new level. Each upgrade first stores the amounts up to that
  moment, with the old capacity (the same steps and lock as ADR 0111).
- **Upgrade cost** from level L to L+1, rounded down. No deuterium:

  | Building | Metal | Crystal |
  |---|---|---|
  | `metal_storage` | 1000 · 2^L | 0 |
  | `crystal_storage` | 1000 · 2^L | 500 · 2^L |
  | `deuterium_tank` | 1000 · 2^L | 1000 · 2^L |

- **Storage uses no energy and produces nothing.** A storage building has
  `production_per_hour` 0 and `energy` 0 and 0.
- **The vault shows the capacity.** `Vault.capacity` is a `Resources` object.

## Consequences

- `read_vault`, `list_buildings`, and `upgrade_building` are `x-planned` in the
  prep, because their responses changed. The cleanup removes the flags.
- No new schema, so `frontend/src/lib/api.ts` needs no new export (lesson 17).
