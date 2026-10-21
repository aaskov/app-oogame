import math
from datetime import datetime
from uuid import UUID

from app.modules.planets._internal.models import (
    MAX_AMOUNT,
    MINE_ORDER,
    Mine,
    MineKind,
    MineUpgrade,
    Planet,
    Resources,
    StoredVault,
    Vault,
)
from app.modules.planets._internal.repository import PlanetRepository
from app.shared.config import Settings

# Mine production per hour at level L, before GAME_SPEED (docs/adr/0111).
_MINE_COEFFICIENT: dict[MineKind, int] = {
    "metal_mine": 30,
    "crystal_mine": 20,
    "deuterium_synthesizer": 10,
}

# The base income of each planet per hour, before GAME_SPEED (docs/adr/0111).
_BASE_INCOME = Resources(metal=30, crystal=15, deuterium=0)

# (metal base, crystal base, ratio) for the cost of the next level (docs/adr/0111).
_UPGRADE_COST: dict[MineKind, tuple[float, float, float]] = {
    "metal_mine": (60, 15, 1.5),
    "crystal_mine": (48, 24, 1.6),
    "deuterium_synthesizer": (225, 75, 1.5),
}


class InsufficientResourcesError(Exception):
    """The vault does not have enough to pay an upgrade's cost (docs/adr/0111)."""


def _clamp(amount: int) -> int:
    return min(amount, MAX_AMOUNT)


def _mine_production_per_hour(kind: MineKind, level: int, game_speed: float) -> int:
    raw = _MINE_COEFFICIENT[kind] * level * 1.1**level
    return _clamp(math.floor(raw * game_speed))


def _upgrade_cost(kind: MineKind, level: int) -> Resources:
    metal_base, crystal_base, ratio = _UPGRADE_COST[kind]
    return Resources(
        metal=_clamp(math.floor(metal_base * ratio**level)),
        crystal=_clamp(math.floor(crystal_base * ratio**level)),
        deuterium=0,
    )


def _vault_production_per_hour(levels: dict[str, int], game_speed: float) -> Resources:
    return Resources(
        metal=_clamp(
            math.floor(_BASE_INCOME.metal * game_speed)
            + _mine_production_per_hour("metal_mine", levels.get("metal_mine", 0), game_speed)
        ),
        crystal=_clamp(
            math.floor(_BASE_INCOME.crystal * game_speed)
            + _mine_production_per_hour("crystal_mine", levels.get("crystal_mine", 0), game_speed)
        ),
        deuterium=_clamp(
            math.floor(_BASE_INCOME.deuterium * game_speed)
            + _mine_production_per_hour(
                "deuterium_synthesizer", levels.get("deuterium_synthesizer", 0), game_speed
            )
        ),
    )


def _calculate_amount(stored: int, production_per_hour: int, hours: float) -> int:
    return _clamp(math.floor(stored + production_per_hour * hours))


class PlanetService:
    def __init__(self, repository: PlanetRepository, settings: Settings, now: datetime) -> None:
        self._repository = repository
        self._settings = settings
        self._now = now

    def list_planets(self, user_id: UUID) -> list[Planet]:
        planets = self._repository.list_for_user(user_id)
        if planets:
            return planets
        self._repository.create_home_planet(user_id)
        return self._repository.list_for_user(user_id)

    def read_vault(self, planet_id: UUID, user_id: UUID) -> Vault | None:
        row = self._repository.get_vault(planet_id, user_id)
        if row is None:
            return None
        levels = self._repository.get_building_levels(planet_id)
        return self._vault_from_row(row, levels)

    def list_mines(self, planet_id: UUID, user_id: UUID) -> list[Mine] | None:
        if not self._repository.planet_owned_by(planet_id, user_id):
            return None
        levels = self._repository.get_building_levels(planet_id)
        game_speed = self._settings.game_speed
        return [
            Mine(
                kind=kind,
                level=levels.get(kind, 0),
                production_per_hour=_mine_production_per_hour(
                    kind, levels.get(kind, 0), game_speed
                ),
                upgrade_cost=_upgrade_cost(kind, levels.get(kind, 0)),
            )
            for kind in MINE_ORDER
        ]

    def upgrade_mine(self, planet_id: UUID, user_id: UUID, kind: MineKind) -> MineUpgrade | None:
        """Lock the vault, store the production up to now, and pay for the upgrade.

        Raises InsufficientResourcesError, and rolls back, if the vault has too
        little. One transaction, so two upgrades at the same time cannot spend
        the same resources (docs/adr/0111).
        """
        vault_row = self._repository.lock_vault(planet_id, user_id)
        if vault_row is None:
            return None
        levels = self._repository.get_building_levels(planet_id)
        level = levels.get(kind, 0)
        game_speed = self._settings.game_speed
        vault = self._vault_from_row(vault_row, levels)
        cost = _upgrade_cost(kind, level)
        insufficient = (
            vault.metal < cost.metal
            or vault.crystal < cost.crystal
            or vault.deuterium < cost.deuterium
        )
        if insufficient:
            self._repository.rollback()
            raise InsufficientResourcesError("Not enough resources for the upgrade")

        metal = vault.metal - cost.metal
        crystal = vault.crystal - cost.crystal
        deuterium = vault.deuterium - cost.deuterium
        self._repository.update_vault_amounts(planet_id, metal, crystal, deuterium, self._now)
        self._repository.set_building_level(planet_id, kind, level + 1)
        self._repository.commit()

        new_levels = {**levels, kind: level + 1}
        mine = Mine(
            kind=kind,
            level=level + 1,
            production_per_hour=_mine_production_per_hour(kind, level + 1, game_speed),
            upgrade_cost=_upgrade_cost(kind, level + 1),
        )
        new_vault = Vault(
            planet_id=planet_id,
            metal=metal,
            crystal=crystal,
            deuterium=deuterium,
            production_per_hour=_vault_production_per_hour(new_levels, game_speed),
            calculated_at=self._now,
        )
        return MineUpgrade(mine=mine, vault=new_vault)

    def _vault_from_row(self, row: StoredVault, levels: dict[str, int]) -> Vault:
        production = _vault_production_per_hour(levels, self._settings.game_speed)
        hours = (self._now - row.updated_at).total_seconds() / 3600
        return Vault(
            planet_id=row.planet_id,
            metal=_calculate_amount(row.metal, production.metal, hours),
            crystal=_calculate_amount(row.crystal, production.crystal, hours),
            deuterium=_calculate_amount(row.deuterium, production.deuterium, hours),
            production_per_hour=production,
            calculated_at=self._now,
        )
