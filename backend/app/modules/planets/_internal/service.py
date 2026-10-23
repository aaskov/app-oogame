import math
from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID

from app.modules.planets._internal.models import (
    BUILDING_ORDER,
    MAX_AMOUNT,
    Building,
    BuildingKind,
    BuildingUpgrade,
    Construction,
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

# (metal base, crystal base, ratio) for the cost of the next level (docs/adr/0111, 0112, 0113).
_UPGRADE_COST: dict[BuildingKind, tuple[float, float, float]] = {
    "metal_mine": (60, 15, 1.5),
    "crystal_mine": (48, 24, 1.6),
    "deuterium_synthesizer": (225, 75, 1.5),
    "solar_plant": (75, 30, 1.5),
    "metal_storage": (1000, 0, 2.0),
    "crystal_storage": (1000, 500, 2.0),
    "deuterium_tank": (1000, 1000, 2.0),
}


class InsufficientResourcesError(Exception):
    """The vault does not have enough to pay an upgrade's cost (docs/adr/0111)."""


class UpgradeRunningError(Exception):
    """An upgrade already runs on the planet (docs/adr/0114)."""


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


def _build_time_seconds(cost: Resources, game_speed: float) -> int:
    """Seconds, rounded down, at least 1 (docs/adr/0114)."""
    return max(1, math.floor(3600 * (cost.metal + cost.crystal) / 2500 / game_speed))


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


def _storage_capacity(level: int) -> int:
    """The capacity at the given storage building level (docs/adr/0113)."""
    exponent = 20 * level / 33
    return _clamp(5000 * math.floor(2.5 * math.exp(exponent)))


def _vault_capacity(levels: dict[str, int]) -> Resources:
    """The capacity of each resource, determined by storage building levels."""
    return Resources(
        metal=_storage_capacity(levels.get("metal_storage", 0)),
        crystal=_storage_capacity(levels.get("crystal_storage", 0)),
        deuterium=_storage_capacity(levels.get("deuterium_tank", 0)),
    )


def _calculate_amount(stored: int, production_per_hour: int, hours: float, capacity: int) -> int:
    """Calculate the amount of a resource, capped at capacity (docs/adr/0113)."""
    if stored >= capacity:
        return _clamp(stored)
    return _clamp(min(capacity, math.floor(stored + production_per_hour * hours)))


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
        self._complete_due(planet_id, user_id)
        row = self._repository.get_vault(planet_id, user_id)
        if row is None:
            return None
        levels = self._repository.get_building_levels(planet_id)
        return self._vault_from_row(row, levels, self._now)

    def list_buildings(self, planet_id: UUID, user_id: UUID) -> list[Building] | None:
        if not self._repository.planet_owned_by(planet_id, user_id):
            return None
        self._complete_due(planet_id, user_id)
        levels = self._repository.get_building_levels(planet_id)
        construction = self._repository.get_construction(planet_id)
        return [self._building(kind, levels, construction) for kind in BUILDING_ORDER]

    def upgrade_building(
        self, planet_id: UUID, user_id: UUID, kind: BuildingKind
    ) -> BuildingUpgrade | None:
        """Start an upgrade: the four steps of docs/adr/0114, in one transaction.

        Raises UpgradeRunningError if an upgrade still runs, and
        InsufficientResourcesError if the vault has too little. Both roll back.
        Returns the building with the old level and the vault after the cost.
        """
        vault_row = self._repository.lock_vault(planet_id, user_id)
        if vault_row is None:
            return None
        vault_row, running = self._complete_due_locked(planet_id, vault_row)
        if running is not None:
            self._repository.rollback()
            raise UpgradeRunningError("An upgrade is already running on the planet")

        levels = self._repository.get_building_levels(planet_id)
        level = levels.get(kind, 0)
        vault = self._vault_from_row(vault_row, levels, self._now)
        cost = _upgrade_cost(kind, level)
        insufficient = (
            vault.metal < cost.metal
            or vault.crystal < cost.crystal
            or vault.deuterium < cost.deuterium
        )
        if insufficient:
            self._repository.rollback()
            raise InsufficientResourcesError("Not enough resources for the upgrade")

        finishes_at = self._now + timedelta(
            seconds=_build_time_seconds(cost, self._settings.game_speed)
        )
        metal = vault.metal - cost.metal
        crystal = vault.crystal - cost.crystal
        deuterium = vault.deuterium - cost.deuterium
        # Never store a time before the stored time (docs/adr/0111).
        stored_at = max(self._now, vault_row.updated_at)
        self._repository.update_vault_amounts(planet_id, metal, crystal, deuterium, stored_at)
        self._repository.add_construction(planet_id, kind, finishes_at)
        self._repository.commit()

        construction = Construction(kind=kind, finishes_at=finishes_at)
        new_vault = replace(vault, metal=metal, crystal=crystal, deuterium=deuterium)
        return BuildingUpgrade(building=self._building(kind, levels, construction), vault=new_vault)

    def _complete_due(self, planet_id: UUID, user_id: UUID) -> None:
        """Complete an upgrade that is due, before a read (docs/adr/0114).

        Takes the vault lock only if an upgrade is due. Another request can
        complete it while this one waits, so the row is read again after the lock.
        """
        construction = self._repository.get_construction(planet_id)
        if construction is None or construction.finishes_at > self._now:
            return
        vault_row = self._repository.lock_vault(planet_id, user_id)
        if vault_row is None:
            return
        self._complete_due_locked(planet_id, vault_row)
        self._repository.commit()

    def _complete_due_locked(
        self, planet_id: UUID, vault_row: StoredVault
    ) -> tuple[StoredVault, Construction | None]:
        """Complete a due upgrade, with the vault lock held. The caller commits.

        Stores the amounts up to the finish time with the old levels, raises the
        level, and deletes the row. Returns the stored vault and the upgrade
        that still runs, if any.
        """
        construction = self._repository.get_construction(planet_id)
        if construction is None or construction.finishes_at > self._now:
            return vault_row, construction
        levels = self._repository.get_building_levels(planet_id)
        # Never store a time before the stored time (docs/adr/0111).
        stored_at = max(construction.finishes_at, vault_row.updated_at)
        vault = self._vault_from_row(vault_row, levels, stored_at)
        self._repository.update_vault_amounts(
            planet_id, vault.metal, vault.crystal, vault.deuterium, stored_at
        )
        self._repository.set_building_level(
            planet_id, construction.kind, levels.get(construction.kind, 0) + 1
        )
        self._repository.delete_construction(planet_id)
        stored = StoredVault(
            planet_id=planet_id,
            metal=vault.metal,
            crystal=vault.crystal,
            deuterium=vault.deuterium,
            updated_at=stored_at,
        )
        return stored, None

    def _building(
        self, kind: BuildingKind, levels: dict[str, int], construction: Construction | None
    ) -> Building:
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
            upgrade_finishes_at=(
                construction.finishes_at
                if construction is not None and construction.kind == kind
                else None
            ),
        )

    def _vault_from_row(self, row: StoredVault, levels: dict[str, int], at: datetime) -> Vault:
        energy = _planet_energy(levels)
        production = _vault_production_per_hour(
            levels, _energy_factor(energy), self._settings.game_speed
        )
        capacity = _vault_capacity(levels)
        # A request can read its time, then wait for an upgrade that stores a
        # later time. Negative hours count as 0 (docs/adr/0111).
        hours = max(0.0, (at - row.updated_at).total_seconds() / 3600)
        return Vault(
            planet_id=row.planet_id,
            metal=_calculate_amount(row.metal, production.metal, hours, capacity.metal),
            crystal=_calculate_amount(row.crystal, production.crystal, hours, capacity.crystal),
            deuterium=_calculate_amount(
                row.deuterium, production.deuterium, hours, capacity.deuterium
            ),
            production_per_hour=production,
            energy=energy,
            capacity=capacity,
            calculated_at=at,
        )
