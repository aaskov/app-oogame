# 0112 — Energy: a solar plant, and mines that use energy

**Status:** Accepted · 2026-10-22

## Context

ADR 0111 added three mines without energy. In OGame, each mine uses energy,
and a solar plant produces it. If the energy is too low, the mines produce
less. This makes the choice of the next upgrade a real game choice.

## Decision

- **A fourth building kind, `solar_plant`.** It uses the `buildings` table.
  A migration adds `solar_plant` to the check constraint `known_kind`.
- **The API changes from "mines" to "buildings".** The new operations are
  `list_buildings` (`GET /planets/{planet_id}/buildings`) and
  `upgrade_building` (`POST /planets/{planet_id}/buildings/{kind}/upgrade`).
  The list always has four buildings, in the order `metal_mine`,
  `crystal_mine`, `deuterium_synthesizer`, `solar_plant`.
- **Energy per building**, at level L, rounded down. `GAME_SPEED` does not
  change the energy:

  | Building | Produces | Uses |
  |---|---|---|
  | `metal_mine` | 0 | 10 · L · 1.1^L |
  | `crystal_mine` | 0 | 10 · L · 1.1^L |
  | `deuterium_synthesizer` | 0 | 20 · L · 1.1^L |
  | `solar_plant` | 20 · L · 1.1^L | 0 |

  The planet's `energy.produced` is the sum of the produced energy. The
  planet's `energy.used` is the sum of the used energy.
- **The energy factor** is `min(1, produced / used)`, not rounded. If `used`
  is 0, the factor is 1. The factor applies to the production of each mine.
  It does not apply to the base income:

  `mine production = floor(coefficient · L · 1.1^L · factor · GAME_SPEED)`

  The coefficients and the base income are in ADR 0111.
- **The production stays calculated on read.** The energy changes only when a
  building gets a new level. Each upgrade first stores the production up to
  that moment, with the old factor. So the factor is constant between two
  writes, and the formula of ADR 0111 stays exact.
- **Upgrade cost of the solar plant** from level L to L+1, rounded down:
  75 · 1.5^L metal, 30 · 1.5^L crystal, no deuterium.
- **An upgrade that makes the energy too low is allowed.** The upgrade of a
  building follows the same steps and the same lock as ADR 0111.
- **The vault shows the energy.** `Vault.energy` has `produced` and `used`.
  Each `Building` has its own `energy`. A mine has `produced` 0. The solar
  plant has `used` 0 and `production_per_hour` 0.

## The change of the API in two steps

The gate requires that the backend serves exactly the contract operations.
So the change goes in two steps:

1. **Expand.** The contract keeps `list_mines` and `upgrade_mine`, and adds
   the buildings operations as `x-planned`. The vault gets `energy`, so
   `read_vault` and `upgrade_mine` are `x-planned` until the backend returns
   the energy. Until the cleanup, the mines operations show the production
   after the energy factor.
2. **Contract.** After the frontend uses the buildings operations, the
   architect removes `list_mines`, `upgrade_mine`, `Mine`, `MineKind`, and
   `MineUpgrade` from the contract and the backend.

Both steps are done. The expand step is in #39 and #40. The agents did the
work in #43 and #44. The contract step is in contract 0.6.0.

## Consequences

- A new player who upgrades a mine before the solar plant gets only the base
  income from that resource, because the factor is 0.
- Storage (a limit for each resource) can be a later building kind in the
  same table.
