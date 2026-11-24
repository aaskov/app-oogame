import math
import random
from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID

from app.modules.planets._internal.models import (
    BUILDING_ORDER,
    HOME_POSITIONS,
    MAX_AMOUNT,
    POSITIONS_PER_SYSTEM,
    SHIP_ORDER,
    TECH_ORDER,
    Building,
    BuildingKind,
    BuildingUpgrade,
    Construction,
    Energy,
    GalaxyPlanet,
    GalaxyPosition,
    GalaxySystem,
    Planet,
    Research,
    ResearchStart,
    Resources,
    RunningResearch,
    Ship,
    ShipKind,
    ShipOrder,
    ShipOrderResult,
    Shipyard,
    StoredResearch,
    StoredShipOrder,
    StoredVault,
    TechKind,
    Technology,
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

# Energy at level L is coefficient · L · 1.1^L, rounded down (docs/adr/0112, 0117).
_ENERGY_PRODUCED_COEFFICIENT: dict[str, int] = {"solar_plant": 20}
_ENERGY_USED_COEFFICIENT: dict[str, int] = {
    "metal_mine": 10,
    "crystal_mine": 10,
    "deuterium_synthesizer": 20,
}

# The plasma technology bonus on mine production, 0.01 · P for metal, 0.0066 · P
# for crystal, 0.0033 · P for deuterium. It does not apply to the base income
# (docs/adr/0117).
_PLASMA_BONUS_COEFFICIENT: dict[str, float] = {
    "metal_mine": 0.01,
    "crystal_mine": 0.0066,
    "deuterium_synthesizer": 0.0033,
}

# The base income of each planet per hour, before GAME_SPEED (docs/adr/0111).
_BASE_INCOME = Resources(metal=30, crystal=15, deuterium=0)

# (metal base, crystal base, ratio) for the next level's cost (docs/adr/0111 to 0113, 0117).
_UPGRADE_COST: dict[BuildingKind, tuple[float, float, float]] = {
    "metal_mine": (60, 15, 1.5),
    "crystal_mine": (48, 24, 1.6),
    "deuterium_synthesizer": (225, 75, 1.5),
    "solar_plant": (75, 30, 1.5),
    "metal_storage": (1000, 0, 2.0),
    "crystal_storage": (1000, 500, 2.0),
    "deuterium_tank": (1000, 1000, 2.0),
    "shipyard": (400, 200, 2.0),
    "research_lab": (200, 400, 2.0),
}
# The deuterium base of the next level's cost. Only the shipyard and the
# research lab have one (docs/adr/0115, 0117).
_UPGRADE_DEUTERIUM: dict[BuildingKind, float] = {"shipyard": 100, "research_lab": 200}

# The cost of one ship (docs/adr/0115).
_SHIP_COST: dict[ShipKind, Resources] = {
    "small_cargo": Resources(metal=2000, crystal=2000, deuterium=0),
    "light_fighter": Resources(metal=3000, crystal=1000, deuterium=0),
}

# The cost of the next technology level, before the 2^L growth (docs/adr/0117).
_TECH_COST_BASE: dict[TechKind, Resources] = {
    "energy_technology": Resources(metal=0, crystal=800, deuterium=400),
    "plasma_technology": Resources(metal=2000, crystal=4000, deuterium=1000),
}
_TECH_RATIO = 2.0

# The technology level a technology needs before it is available (docs/adr/0117).
_TECH_REQUIREMENTS: dict[TechKind, tuple[TechKind, int]] = {
    "plasma_technology": ("energy_technology", 1),
}


class InsufficientResourcesError(Exception):
    """The vault does not have enough to pay an upgrade's cost (docs/adr/0111)."""


class UpgradeRunningError(Exception):
    """An upgrade already runs on the planet (docs/adr/0114)."""


class NoShipyardError(Exception):
    """The shipyard has level 0 (docs/adr/0115)."""


class ShipOrderRunningError(Exception):
    """A ship order already runs on the planet (docs/adr/0115)."""


class NoLabError(Exception):
    """The research lab of the planet has level 0 (docs/adr/0117)."""


class ResearchRunningError(Exception):
    """A research already runs for the player (docs/adr/0117)."""


class TechnologyNotAvailableError(Exception):
    """A required technology level is missing (docs/adr/0117)."""


class NoFreePositionError(Exception):
    """No position from 4 to 12 is free anywhere in the universe (docs/adr/0118)."""


def _clamp(amount: int) -> int:
    return min(amount, MAX_AMOUNT)


def _building_energy(kind: str, level: int, energy_tech_level: int) -> Energy:
    growth = level * 1.1**level
    produced_coefficient = _ENERGY_PRODUCED_COEFFICIENT.get(kind, 0)
    if kind == "solar_plant":
        produced = math.floor(produced_coefficient * growth * (1 + 0.1 * energy_tech_level))
    else:
        produced = math.floor(produced_coefficient * growth)
    return Energy(
        produced=produced,
        used=math.floor(_ENERGY_USED_COEFFICIENT.get(kind, 0) * growth),
    )


def _planet_energy(levels: dict[str, int], energy_tech_level: int) -> Energy:
    energies = [_building_energy(kind, level, energy_tech_level) for kind, level in levels.items()]
    return Energy(
        produced=sum(energy.produced for energy in energies),
        used=sum(energy.used for energy in energies),
    )


def _energy_factor(energy: Energy) -> float:
    if energy.used == 0:
        return 1.0
    return min(1.0, energy.produced / energy.used)


def _mine_production_per_hour(
    kind: str, level: int, factor: float, game_speed: float, plasma_tech_level: int
) -> int:
    """The production of one building. 0 for a building that is not a mine."""
    raw = _MINE_COEFFICIENT.get(kind, 0) * level * 1.1**level
    bonus = _PLASMA_BONUS_COEFFICIENT.get(kind, 0.0) * plasma_tech_level
    return _clamp(math.floor(raw * factor * (1 + bonus) * game_speed))


def _upgrade_cost(kind: BuildingKind, level: int) -> Resources:
    metal_base, crystal_base, ratio = _UPGRADE_COST[kind]
    return Resources(
        metal=_clamp(math.floor(metal_base * ratio**level)),
        crystal=_clamp(math.floor(crystal_base * ratio**level)),
        deuterium=_clamp(math.floor(_UPGRADE_DEUTERIUM.get(kind, 0) * ratio**level)),
    )


def _build_time_seconds(cost: Resources, game_speed: float) -> int:
    """Seconds, rounded down, at least 1 (docs/adr/0114)."""
    return max(1, math.floor(3600 * (cost.metal + cost.crystal) / 2500 / game_speed))


def _ship_build_seconds(cost: Resources, shipyard_level: int, game_speed: float) -> int:
    """Seconds for one ship, rounded down, at least 1 (docs/adr/0115)."""
    return max(
        1,
        math.floor(3600 * (cost.metal + cost.crystal) / 2500 / (1 + shipyard_level) / game_speed),
    )


def _research_time_seconds(cost: Resources, lab_level: int, game_speed: float) -> int:
    """Seconds, rounded down, at least 1 (docs/adr/0117)."""
    return max(
        1, math.floor(3600 * (cost.metal + cost.crystal) / 1000 / (1 + lab_level) / game_speed)
    )


def _tech_cost(kind: TechKind, level: int) -> Resources:
    base = _TECH_COST_BASE[kind]
    return Resources(
        metal=_clamp(math.floor(base.metal * _TECH_RATIO**level)),
        crystal=_clamp(math.floor(base.crystal * _TECH_RATIO**level)),
        deuterium=_clamp(math.floor(base.deuterium * _TECH_RATIO**level)),
    )


def _technology_available(kind: TechKind, tech_levels: dict[str, int]) -> bool:
    requirement = _TECH_REQUIREMENTS.get(kind)
    if requirement is None:
        return True
    required_kind, required_level = requirement
    return tech_levels.get(required_kind, 0) >= required_level


def _vault_production_per_hour(
    levels: dict[str, int], factor: float, game_speed: float, plasma_tech_level: int
) -> Resources:
    def per_hour(base: int, kind: str) -> int:
        level = levels.get(kind, 0)
        mine = _mine_production_per_hour(kind, level, factor, game_speed, plasma_tech_level)
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
        self._create_home_planet(user_id)
        return self._repository.list_for_user(user_id)

    def _create_home_planet(self, user_id: UUID) -> None:
        """Create the home planet at a random free position from 4 to 12, in a
        random system of a random galaxy, inside the settings (docs/adr/0118).

        Tries another free position if the insert hits uq_planets_coordinates.
        Raises NoFreePositionError if no position from 4 to 12 is free.
        """
        occupied = self._repository.occupied_positions(
            min(HOME_POSITIONS), max(HOME_POSITIONS)
        )
        candidates = [
            (galaxy, system, position)
            for galaxy in range(1, self._settings.galaxies + 1)
            for system in range(1, self._settings.systems_per_galaxy + 1)
            for position in HOME_POSITIONS
            if (galaxy, system, position) not in occupied
        ]
        random.shuffle(candidates)
        for galaxy, system, position in candidates:
            created_id = self._repository.try_create_home_planet(user_id, galaxy, system, position)
            if created_id is not None:
                self._repository.commit()
                return
            if self._repository.home_planet_exists(user_id):
                self._repository.rollback()
                return
        self._repository.rollback()
        raise NoFreePositionError("No free position from 4 to 12 in the universe")

    def read_galaxy_system(self, galaxy: int, system: int) -> GalaxySystem | None:
        """The 15 positions of one system, or None if the galaxy or the system
        is larger than the universe (docs/adr/0118)."""
        if galaxy > self._settings.galaxies or system > self._settings.systems_per_galaxy:
            return None
        occupants = self._repository.planets_in_system(galaxy, system)
        positions = [
            GalaxyPosition(position=position, planet=self._galaxy_planet(occupants, position))
            for position in range(1, POSITIONS_PER_SYSTEM + 1)
        ]
        return GalaxySystem(
            galaxy=galaxy,
            system=system,
            galaxies=self._settings.galaxies,
            systems_per_galaxy=self._settings.systems_per_galaxy,
            positions=positions,
        )

    def _galaxy_planet(
        self, occupants: dict[int, tuple[str, str]], position: int
    ) -> GalaxyPlanet | None:
        occupant = occupants.get(position)
        return GalaxyPlanet(name=occupant[0], username=occupant[1]) if occupant else None

    def read_vault(self, planet_id: UUID, user_id: UUID) -> Vault | None:
        self._complete_due_research(user_id)
        self._complete_due(planet_id, user_id)
        row = self._repository.get_vault(planet_id, user_id)
        if row is None:
            return None
        levels = self._repository.get_building_levels(planet_id)
        tech_levels = self._repository.get_technology_levels(user_id)
        return self._vault_from_row(row, levels, tech_levels, self._now)

    def list_buildings(self, planet_id: UUID, user_id: UUID) -> list[Building] | None:
        if not self._repository.planet_owned_by(planet_id, user_id):
            return None
        self._complete_due_research(user_id)
        self._complete_due(planet_id, user_id)
        levels = self._repository.get_building_levels(planet_id)
        construction = self._repository.get_construction(planet_id)
        tech_levels = self._repository.get_technology_levels(user_id)
        return [self._building(kind, levels, construction, tech_levels) for kind in BUILDING_ORDER]

    def upgrade_building(
        self, planet_id: UUID, user_id: UUID, kind: BuildingKind
    ) -> BuildingUpgrade | None:
        """Start an upgrade: the four steps of docs/adr/0114, in one transaction.

        Raises UpgradeRunningError if an upgrade still runs, and
        InsufficientResourcesError if the vault has too little. Both roll back.
        Returns the building with the old level and the vault after the cost.
        """
        self._complete_due_research(user_id)
        vault_row = self._repository.lock_vault(planet_id, user_id)
        if vault_row is None:
            return None
        tech_levels = self._repository.get_technology_levels(user_id)
        vault_row, running = self._complete_due_locked(planet_id, vault_row, tech_levels)
        if running is not None:
            self._repository.rollback()
            raise UpgradeRunningError("An upgrade is already running on the planet")

        levels = self._repository.get_building_levels(planet_id)
        level = levels.get(kind, 0)
        vault = self._vault_from_row(vault_row, levels, tech_levels, self._now)
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
        return BuildingUpgrade(
            building=self._building(kind, levels, construction, tech_levels), vault=new_vault
        )

    def read_shipyard(self, planet_id: UUID, user_id: UUID) -> Shipyard | None:
        if not self._repository.planet_owned_by(planet_id, user_id):
            return None
        self._complete_due(planet_id, user_id)
        self._complete_due_ships(planet_id, user_id)
        return self._shipyard(planet_id)

    def order_ships(
        self, planet_id: UUID, user_id: UUID, kind: ShipKind, count: int
    ) -> ShipOrderResult | None:
        """Start a ship order: the five steps of docs/adr/0115, in one transaction.

        Raises NoShipyardError, ShipOrderRunningError, or InsufficientResourcesError.
        Each of them rolls back. Returns the shipyard with the new order and the
        vault after the cost.
        """
        self._complete_due_research(user_id)
        vault_row = self._repository.lock_vault(planet_id, user_id)
        if vault_row is None:
            return None
        tech_levels = self._repository.get_technology_levels(user_id)
        # A due shipyard upgrade changes the level and the stored vault.
        vault_row, _ = self._complete_due_locked(planet_id, vault_row, tech_levels)
        running = self._complete_due_ships_locked(planet_id)

        levels = self._repository.get_building_levels(planet_id)
        shipyard_level = levels.get("shipyard", 0)
        if shipyard_level == 0:
            self._repository.rollback()
            raise NoShipyardError("The shipyard has level 0")
        if running is not None:
            self._repository.rollback()
            raise ShipOrderRunningError("A ship order is already running on the planet")

        vault = self._vault_from_row(vault_row, levels, tech_levels, self._now)
        unit = _SHIP_COST[kind]
        cost = Resources(
            metal=unit.metal * count,
            crystal=unit.crystal * count,
            deuterium=unit.deuterium * count,
        )
        if (
            vault.metal < cost.metal
            or vault.crystal < cost.crystal
            or vault.deuterium < cost.deuterium
        ):
            self._repository.rollback()
            raise InsufficientResourcesError("Not enough resources for the ships")

        seconds_per_ship = _ship_build_seconds(unit, shipyard_level, self._settings.game_speed)
        metal = vault.metal - cost.metal
        crystal = vault.crystal - cost.crystal
        deuterium = vault.deuterium - cost.deuterium
        # Never store a time before the stored time (docs/adr/0111).
        stored_at = max(self._now, vault_row.updated_at)
        self._repository.update_vault_amounts(planet_id, metal, crystal, deuterium, stored_at)
        self._repository.add_ship_order(
            planet_id,
            kind,
            count,
            seconds_per_ship,
            self._now + timedelta(seconds=seconds_per_ship),
        )
        self._repository.commit()

        new_vault = replace(vault, metal=metal, crystal=crystal, deuterium=deuterium)
        return ShipOrderResult(shipyard=self._shipyard(planet_id), vault=new_vault)

    def _complete_due_ships(self, planet_id: UUID, user_id: UUID) -> None:
        """Complete the ships that are due, before a read (docs/adr/0115).

        Takes the vault lock only if a ship is due. Another request can
        complete the ships while this one waits, so the row is read again after the lock.
        """
        order = self._repository.get_ship_order(planet_id)
        if order is None or order.next_finishes_at > self._now:
            return
        if self._repository.lock_vault(planet_id, user_id) is None:
            return
        self._complete_due_ships_locked(planet_id)
        self._repository.commit()

    def _complete_due_ships_locked(self, planet_id: UUID) -> StoredShipOrder | None:
        """Add the due ships to the count, with the vault lock held. The caller commits.

        Returns the order that still runs, if any.
        """
        order = self._repository.get_ship_order(planet_id)
        if order is None or order.next_finishes_at > self._now:
            return order
        overdue = (self._now - order.next_finishes_at).total_seconds()
        done = min(order.remaining, 1 + math.floor(overdue / order.seconds_per_ship))
        self._repository.add_ships(planet_id, order.kind, done)
        if done == order.remaining:
            self._repository.delete_ship_order(planet_id)
            return None
        next_finishes_at = order.next_finishes_at + timedelta(seconds=done * order.seconds_per_ship)
        self._repository.update_ship_order(planet_id, order.remaining - done, next_finishes_at)
        return replace(
            order, remaining=order.remaining - done, next_finishes_at=next_finishes_at
        )

    def _shipyard(self, planet_id: UUID) -> Shipyard:
        levels = self._repository.get_building_levels(planet_id)
        counts = self._repository.get_ship_counts(planet_id)
        shipyard_level = levels.get("shipyard", 0)
        ships = [
            Ship(
                kind=kind,
                count=counts.get(kind, 0),
                cost=_SHIP_COST[kind],
                build_seconds=_ship_build_seconds(
                    _SHIP_COST[kind], shipyard_level, self._settings.game_speed
                ),
            )
            for kind in SHIP_ORDER
        ]
        stored = self._repository.get_ship_order(planet_id)
        order = (
            ShipOrder(
                kind=stored.kind,
                remaining=stored.remaining,
                next_finishes_at=stored.next_finishes_at,
                finishes_at=stored.next_finishes_at
                + timedelta(seconds=(stored.remaining - 1) * stored.seconds_per_ship),
            )
            if stored is not None
            else None
        )
        return Shipyard(ships=ships, order=order)

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
        tech_levels = self._repository.get_technology_levels(user_id)
        self._complete_due_locked(planet_id, vault_row, tech_levels)
        self._repository.commit()

    def _complete_due_locked(
        self, planet_id: UUID, vault_row: StoredVault, tech_levels: dict[str, int]
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
        vault = self._vault_from_row(vault_row, levels, tech_levels, stored_at)
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
        self,
        kind: BuildingKind,
        levels: dict[str, int],
        construction: Construction | None,
        tech_levels: dict[str, int],
    ) -> Building:
        level = levels.get(kind, 0)
        energy_tech_level = tech_levels.get("energy_technology", 0)
        plasma_tech_level = tech_levels.get("plasma_technology", 0)
        factor = _energy_factor(_planet_energy(levels, energy_tech_level))
        return Building(
            kind=kind,
            level=level,
            production_per_hour=_mine_production_per_hour(
                kind, level, factor, self._settings.game_speed, plasma_tech_level
            ),
            energy=_building_energy(kind, level, energy_tech_level),
            upgrade_cost=_upgrade_cost(kind, level),
            upgrade_finishes_at=(
                construction.finishes_at
                if construction is not None and construction.kind == kind
                else None
            ),
        )

    def _vault_from_row(
        self, row: StoredVault, levels: dict[str, int], tech_levels: dict[str, int], at: datetime
    ) -> Vault:
        energy_tech_level = tech_levels.get("energy_technology", 0)
        plasma_tech_level = tech_levels.get("plasma_technology", 0)
        energy = _planet_energy(levels, energy_tech_level)
        production = _vault_production_per_hour(
            levels, _energy_factor(energy), self._settings.game_speed, plasma_tech_level
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

    def read_research(self, user_id: UUID) -> Research:
        self._complete_due_research(user_id)
        tech_levels = self._repository.get_technology_levels(user_id)
        running = self._repository.get_research(user_id)
        return self._research(tech_levels, running)

    def start_research(
        self, planet_id: UUID, user_id: UUID, kind: TechKind
    ) -> ResearchStart | None:
        """Start a research: the six steps of docs/adr/0117, in one transaction.

        Raises NoLabError, ResearchRunningError, TechnologyNotAvailableError, or
        InsufficientResourcesError. Each of them rolls back. Returns the research
        with the new running research, and the vault of the planet after the cost.
        """
        if not self._repository.planet_owned_by(planet_id, user_id):
            return None

        # Lock the vaults of every planet of the player, in the order of the
        # planet ID, so a research that completes changes every planet's
        # production consistently, and two starts of the player cannot race.
        planet_ids = self._repository.list_planet_ids_for_user(user_id)
        vault_rows: dict[UUID, StoredVault] = {}
        for pid in planet_ids:
            row = self._repository.lock_vault(pid, user_id)
            if row is not None:
                vault_rows[pid] = row
        vault_rows = self._complete_due_research_locked(user_id, vault_rows)

        vault_row = vault_rows.get(planet_id)
        if vault_row is None:
            self._repository.rollback()
            return None

        tech_levels = self._repository.get_technology_levels(user_id)
        vault_row, _ = self._complete_due_locked(planet_id, vault_row, tech_levels)
        vault_rows[planet_id] = vault_row

        levels = self._repository.get_building_levels(planet_id)
        lab_level = levels.get("research_lab", 0)
        if lab_level == 0:
            self._repository.rollback()
            raise NoLabError("The research lab of the planet has level 0")

        running = self._repository.get_research(user_id)
        if running is not None:
            self._repository.rollback()
            raise ResearchRunningError("A research is already running")

        if not _technology_available(kind, tech_levels):
            self._repository.rollback()
            raise TechnologyNotAvailableError("A required technology level is missing")

        vault = self._vault_from_row(vault_row, levels, tech_levels, self._now)
        cost = _tech_cost(kind, tech_levels.get(kind, 0))
        if (
            vault.metal < cost.metal
            or vault.crystal < cost.crystal
            or vault.deuterium < cost.deuterium
        ):
            self._repository.rollback()
            raise InsufficientResourcesError("Not enough resources for the research")

        finishes_at = self._now + timedelta(
            seconds=_research_time_seconds(cost, lab_level, self._settings.game_speed)
        )
        metal = vault.metal - cost.metal
        crystal = vault.crystal - cost.crystal
        deuterium = vault.deuterium - cost.deuterium
        # Never store a time before the stored time (docs/adr/0111).
        stored_at = max(self._now, vault_row.updated_at)
        self._repository.update_vault_amounts(planet_id, metal, crystal, deuterium, stored_at)
        self._repository.add_research(user_id, kind, planet_id, finishes_at)
        self._repository.commit()

        new_vault = replace(vault, metal=metal, crystal=crystal, deuterium=deuterium)
        running = StoredResearch(kind=kind, planet_id=planet_id, finishes_at=finishes_at)
        research = self._research(tech_levels, running)
        return ResearchStart(research=research, vault=new_vault)

    def _complete_due_research(self, user_id: UUID) -> None:
        """Complete a research that is due, before a read (docs/adr/0117).

        Takes the vault locks of every planet of the player only if a research
        is due. Another request can complete it while this one waits, so the
        research row is read again after the locks.
        """
        research = self._repository.get_research(user_id)
        if research is None or research.finishes_at > self._now:
            return
        planet_ids = self._repository.list_planet_ids_for_user(user_id)
        vault_rows: dict[UUID, StoredVault] = {}
        for planet_id in planet_ids:
            row = self._repository.lock_vault(planet_id, user_id)
            if row is not None:
                vault_rows[planet_id] = row
        self._complete_due_research_locked(user_id, vault_rows)
        self._repository.commit()

    def _complete_due_research_locked(
        self, user_id: UUID, vault_rows: dict[UUID, StoredVault]
    ) -> dict[UUID, StoredVault]:
        """Complete a due research, with the vault locks of every planet of the
        player held. The caller commits.

        On each planet, first completes a building upgrade that is due at or
        before the research's finish time. Then stores the amounts of each
        planet up to that time, with the old technology levels. Finally raises
        the technology level and deletes the research row.

        Returns the vault rows as they are stored now, so a caller that keeps
        completing events in the same transaction does not read the amounts
        and the time from before this completion.
        """
        research = self._repository.get_research(user_id)
        if research is None or research.finishes_at > self._now:
            return vault_rows
        old_tech_levels = self._repository.get_technology_levels(user_id)
        updated_rows = dict(vault_rows)
        for planet_id, vault_row in vault_rows.items():
            levels = self._repository.get_building_levels(planet_id)
            construction = self._repository.get_construction(planet_id)
            if construction is not None and construction.finishes_at <= research.finishes_at:
                vault_row, _ = self._complete_due_locked(planet_id, vault_row, old_tech_levels)
                levels = self._repository.get_building_levels(planet_id)
            stored_at = max(research.finishes_at, vault_row.updated_at)
            vault = self._vault_from_row(vault_row, levels, old_tech_levels, stored_at)
            self._repository.update_vault_amounts(
                planet_id, vault.metal, vault.crystal, vault.deuterium, stored_at
            )
            updated_rows[planet_id] = StoredVault(
                planet_id=planet_id,
                metal=vault.metal,
                crystal=vault.crystal,
                deuterium=vault.deuterium,
                updated_at=stored_at,
            )
        new_level = old_tech_levels.get(research.kind, 0) + 1
        self._repository.set_technology_level(user_id, research.kind, new_level)
        self._repository.delete_research(user_id)
        return updated_rows

    def _research(
        self, tech_levels: dict[str, int], running: StoredResearch | None
    ) -> Research:
        technologies = [
            Technology(
                kind=kind,
                level=tech_levels.get(kind, 0),
                cost=_tech_cost(kind, tech_levels.get(kind, 0)),
                available=_technology_available(kind, tech_levels),
            )
            for kind in TECH_ORDER
        ]
        running_model = (
            RunningResearch(
                kind=running.kind, planet_id=running.planet_id, finishes_at=running.finishes_at
            )
            if running is not None
            else None
        )
        return Research(technologies=technologies, running=running_model)
