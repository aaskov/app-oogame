import math
from datetime import datetime
from uuid import UUID

from app.modules.planets._internal.models import (
    BUILDING_ORDER,
    MAX_AMOUNT,
    Building,
    BuildingKind,
    BuildingUpgrade,
    Energy,
    Planet,
    Resources,
    StoredVault,
    Vault,
)
from app.modules.planets._internal.repository import PlanetRepository
from app.shared.config import Settings

# Mine production per hour at level L, before the factor and GAME_SPEED (docs/adr/0111).
_MINE_COEFFICIENT: dict[str, int] = {
    "metal_mine": 30,
    "crystal_mine": 20,
    "deuterium_synthesizer": 10,
}

# Energy at level L is coefficient · L · 1.1^L, rounded down (docs/adr/0112).
_ENERGY_PRODUCED_COEFFICIENT: dict[str, int] = {"solar_plant": 20}
_ENERGY_USED_COEFFICIENT: dict[str, int] = {
    "metal_mine": 10,
    "crystal_mine": 10,
    "deuterium_synthesizer": 20,
}

# The base income of each planet per hour, before GAME_SPEED (docs/adr/0111).
_BASE_INCOME = Resources(metal=30, crystal=15, deuterium=0)

# (metal base, crystal base, ratio) for the cost of the next level (docs/adr/0111, 0112).
_UPGRADE_COST: dict[BuildingKind, tuple[float, float, float]] = {
    "metal_mine": (60, 15, 1.5),
    "crystal_mine": (48, 24, 1.6),
    "deuterium_synthesizer": (225, 75, 1.5),
    "solar_plant": (75, 30, 1.5),
}


class InsufficientResourcesError(Exception):
    """The vault does not have enough to pay an upgrade's cost (docs/adr/0111)."""


def _clamp(amount: int) -> int:
    return min(amount, MAX_AMOUNT)


def _building_energy(kind: str, level: int) -> Energy:
    growth = level * 1.1**level
    return Energy(
        produced=math.floor(_ENERGY_PRODUCED_COEFFICIENT.get(kind, 0) * growth),
        used=math.floor(_ENERGY_USED_COEFFICIENT.get(kind, 0) * growth),
    )


def _planet_energy(levels: dict[str, int]) -> Energy:
    energies = [_building_energy(kind, level) for kind, level in levels.items()]
    return Energy(
        produced=sum(energy.produced for energy in energies),
        used=sum(energy.used for energy in energies),
    )


def _energy_factor(energy: Energy) -> float:
    if energy.used == 0:
        return 1.0
    return min(1.0, energy.produced / energy.used)


def _mine_production_per_hour(kind: str, level: int, factor: float, game_speed: float) -> int:
    """The production of one building. 0 for a building that is not a mine."""
    raw = _MINE_COEFFICIENT.get(kind, 0) * level * 1.1**level
    return _clamp(math.floor(raw * factor * game_speed))


def _upgrade_cost(kind: BuildingKind, level: int) -> Resources:
    metal_base, crystal_base, ratio = _UPGRADE_COST[kind]
    return Resources(
        metal=_clamp(math.floor(metal_base * ratio**level)),
        crystal=_clamp(math.floor(crystal_base * ratio**level)),
        deuterium=0,
    )


def _vault_production_per_hour(
    levels: dict[str, int], factor: float, game_speed: float
) -> Resources:
    def per_hour(base: int, kind: str) -> int:
        mine = _mine_production_per_hour(kind, levels.get(kind, 0), factor, game_speed)
        return _clamp(math.floor(base * game_speed) + mine)

    return Resources(
        metal=per_hour(_BASE_INCOME.metal, "metal_mine"),
        crystal=per_hour(_BASE_INCOME.crystal, "crystal_mine"),
        deuterium=per_hour(_BASE_INCOME.deuterium, "deuterium_synthesizer"),
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

    def list_buildings(self, planet_id: UUID, user_id: UUID) -> list[Building] | None:
        if not self._repository.planet_owned_by(planet_id, user_id):
            return None
        levels = self._repository.get_building_levels(planet_id)
        return [self._building(kind, levels) for kind in BUILDING_ORDER]

    def upgrade_building(
        self, planet_id: UUID, user_id: UUID, kind: BuildingKind
    ) -> BuildingUpgrade | None:
        result = self._upgrade(planet_id, user_id, kind)
        if result is None:
            return None
        levels, vault = result
        return BuildingUpgrade(building=self._building(kind, levels), vault=vault)

    def _upgrade(
        self, planet_id: UUID, user_id: UUID, kind: BuildingKind
    ) -> tuple[dict[str, int], Vault] | None:
        """Lock the vault, store the production up to now, and pay for the upgrade.

        The production is stored with the old energy factor. Raises
        InsufficientResourcesError, and rolls back, if the vault has too
        little. One transaction, so two upgrades at the same time cannot spend
        the same resources (docs/adr/0111, docs/adr/0112). Returns the levels
        after the upgrade and the vault after the cost.
        """
        vault_row = self._repository.lock_vault(planet_id, user_id)
        if vault_row is None:
            return None
        levels = self._repository.get_building_levels(planet_id)
        level = levels.get(kind, 0)
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
        # Never store a time before the stored time (docs/adr/0111).
        stored_at = max(self._now, vault_row.updated_at)
        self._repository.update_vault_amounts(planet_id, metal, crystal, deuterium, stored_at)
        self._repository.set_building_level(planet_id, kind, level + 1)
        self._repository.commit()

        new_levels = {**levels, kind: level + 1}
        energy = _planet_energy(new_levels)
        new_vault = Vault(
            planet_id=planet_id,
            metal=metal,
            crystal=crystal,
            deuterium=deuterium,
            production_per_hour=_vault_production_per_hour(
                new_levels, _energy_factor(energy), self._settings.game_speed
            ),
            energy=energy,
            calculated_at=self._now,
        )
        return new_levels, new_vault

    def _building(self, kind: BuildingKind, levels: dict[str, int]) -> Building:
        level = levels.get(kind, 0)
        factor = _energy_factor(_planet_energy(levels))
        return Building(
            kind=kind,
            level=level,
            production_per_hour=_mine_production_per_hour(
                kind, level, factor, self._settings.game_speed
            ),
            energy=_building_energy(kind, level),
            upgrade_cost=_upgrade_cost(kind, level),
        )

    def _vault_from_row(self, row: StoredVault, levels: dict[str, int]) -> Vault:
        energy = _planet_energy(levels)
        production = _vault_production_per_hour(
            levels, _energy_factor(energy), self._settings.game_speed
        )
        # A request can read its time, then wait for an upgrade that stores a
        # later time. Negative hours count as 0 (docs/adr/0111).
        hours = max(0.0, (self._now - row.updated_at).total_seconds() / 3600)
        return Vault(
            planet_id=row.planet_id,
            metal=_calculate_amount(row.metal, production.metal, hours),
            crystal=_calculate_amount(row.crystal, production.crystal, hours),
            deuterium=_calculate_amount(row.deuterium, production.deuterium, hours),
            production_per_hour=production,
            energy=energy,
            calculated_at=self._now,
        )
