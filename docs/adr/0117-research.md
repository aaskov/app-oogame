# 0117 — Research: a lab, two technologies of the player, completed on read

**Status:** Accepted · 2026-11-21

## Context

The planet has mines, energy, storage, build time, and a shipyard (ADR 0111
to 0115). In OGame, a research lab researches technologies. A technology
belongs to the player, so it counts on each planet.

## Decision

- **A ninth building kind, `research_lab`.** It uses the `buildings` table. A
  migration adds it to the check constraint `known_kind` of `buildings` and
  `constructions`. The buildings list has nine buildings, with
  `research_lab` last. The upgrade follows ADR 0114. The lab uses no energy
  and produces nothing.
- **Upgrade cost of the research lab** from level L to L+1:
  `200 · 2^L` metal, `400 · 2^L` crystal, `200 · 2^L` deuterium.
- **Two technologies.** The table `technologies` has `user_id`, `kind`, and
  `level`. No row means level 0. Cost from level L to L+1, rounded down:

  | Technology | Metal | Crystal | Deuterium | Needs |
  |---|---|---|---|---|
  | `energy_technology` | 0 | 800 · 2^L | 400 · 2^L | — |
  | `plasma_technology` | 2000 · 2^L | 4000 · 2^L | 1000 · 2^L | energy technology level 1 |

  `Technology.available` is false if a needed level is missing.
- **The effects**, at energy technology level E and plasma technology level P.
  `GAME_SPEED` does not change the energy:
  - Solar plant energy: `floor(20 · L · 1.1^L · (1 + 0.1 · E))`.
  - Mine production:
    `floor(coefficient · L · 1.1^L · factor · (1 + bonus) · GAME_SPEED)`, with
    `bonus` = `0.01 · P` for metal, `0.0066 · P` for crystal, and
    `0.0033 · P` for deuterium. The bonus does not apply to the base income.

  The formulas of ADR 0111 and ADR 0112 stay the same at E = 0 and P = 0.
- **Research time** in seconds, rounded down, at least 1, at lab level S of
  the planet that starts it:
  `3600 · (metal cost + crystal cost) / 1000 / (1 + S) / GAME_SPEED`.
  Energy technology level 0 to 1 at lab level 1 takes 1440 seconds at speed 1.
- **One running research for each player.** The table `researches` has
  `user_id` (the primary key), `kind`, `planet_id`, and `finishes_at`. No row
  means no running research. The research runs separately from the building
  upgrade and the ship order of each planet.
- **Start of a research** (`start_research`), in one transaction:
  1. Complete the events that are due (see below).
  2. If the lab of the planet has level 0: 409, and nothing changes.
  3. If a research runs for the player: 409, and nothing changes.
  4. If a needed technology level is missing: 409, and nothing changes.
  5. Store the amounts of the planet up to now. Check the cost. If the vault
     has too little: 409, and nothing changes.
  6. Subtract the cost. Add the row with
     `finishes_at = now + research time`. The level does not change yet.
  The player pays at the start. There is no cancel. A later lab upgrade does
  not change the time of a running research.
- **Completion on read.** A research with `finishes_at` at or before now is
  due. It changes the production of each planet of the player. So each read of
  a vault, the buildings, or the research, and each start of an upgrade, an
  order, or a research, first completes it:
  1. Take the locks of all vaults of the player, in the order of the planet
     ID. This order prevents a deadlock.
  2. On each planet, first complete a building upgrade that is due at or
     before `finishes_at` (ADR 0114). The events complete in the order of
     their time.
  3. Store the amounts of each planet up to `finishes_at`, with the old
     technology levels.
  4. Raise the level, and delete the row.
  The calculation stays exact, and there is no background job. A stored time
  never goes back (ADR 0111).
- **The answer.** `Research` has the two technologies, in the order
  `energy_technology`, `plasma_technology`. It has `running` only if a
  research runs (no `null`). The 409 `detail` tells which reason applies.

## Consequences

- `list_buildings` and `upgrade_building` are `x-planned` in the prep,
  because `BuildingKind` gets `research_lab`. `read_research` and
  `start_research` are new and `x-planned`. The cleanup removes the flags
  (done after #76 and #77).
- `read_vault` keeps its schema, but its values now depend on the
  technologies. The backend issue covers this.
- The prep adds the label of the lab to the frontend, so that the type check
  passes. The new schemas are exported in `frontend/src/lib/api.ts`
  (lesson 17).
- Research is in the planets module, because it changes the vaults.
