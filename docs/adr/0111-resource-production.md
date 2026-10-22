# 0111 — Resource production: three mines, calculated on read

**Status:** Accepted · 2026-10-21

## Context

A planet has a vault (ADR 0109). Until now, a user set the amounts with
`PATCH /planets/{planet_id}/vault`, which was a cheat. Now mines produce the
resources, and the user spends resources to upgrade a mine.

## Decision

- **Scope:** three mines. An upgrade is instant. No energy, no build time,
  no storage limit. Each one can be a later feature.
- **`PATCH /planets/{planet_id}/vault` is removed**, with its form.
- **Table `buildings`:** `planet_id`, `kind`, `level`. The primary key is
  (`planet_id`, `kind`). Today `kind` allows only the three mines. No row
  means level 0. A later building kind needs a migration of the check constraint.
- **Production is calculated, not stored.** `vaults.updated_at` is the time of
  the stored amounts. A read returns, for each resource:
  `floor(stored + production_per_hour × hours since updated_at)`, at most 2^53 − 1.
  A write first stores that value, with `updated_at` set to the same time.
  A request reads its time before it waits for the lock. So hours below 0
  count as 0, and a write never stores a time before the stored `updated_at`.
- **Production per hour**, at level L, multiplied by `GAME_SPEED` and rounded down:

  | Mine | Mine production | Base income of each planet |
  |---|---|---|
  | `metal_mine` | 30 · L · 1.1^L | 30 |
  | `crystal_mine` | 20 · L · 1.1^L | 15 |
  | `deuterium_synthesizer` | 10 · L · 1.1^L | 0 |

  The vault's `production_per_hour` is the base income plus the mine production.
  A mine's `production_per_hour` is the mine production only.
- **Upgrade cost** from level L to L+1, rounded down. No deuterium:

  | Mine | Metal | Crystal |
  |---|---|---|
  | `metal_mine` | 60 · 1.5^L | 15 · 1.5^L |
  | `crystal_mine` | 48 · 1.6^L | 24 · 1.6^L |
  | `deuterium_synthesizer` | 225 · 1.5^L | 75 · 1.5^L |

- **An upgrade** locks the vault row (`SELECT ... FOR UPDATE`), stores the
  production up to now, checks the cost, subtracts it, and raises the level, in
  one transaction. If the vault has too little: 409, and nothing changes. Two
  upgrades at the same time cannot spend the same resources.
- **`GAME_SPEED`** (setting `game_speed`, default 1) multiplies the production,
  not the cost. In development, set it higher to see production at once.

## Consequences

- No background job. The amounts are exact at each read.
- The frontend can count up from `calculated_at` with `production_per_hour`.
  The server value wins at each new read.
- In the prep, `read_vault` is `x-planned` again, because its response changed.
  `check:contracts` does not compare a planned operation. Until the cleanup,
  the gate does not check the new vault schema.
