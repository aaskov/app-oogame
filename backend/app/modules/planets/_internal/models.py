from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

MAX_AMOUNT = 9007199254740991  # 2^53 - 1, the largest integer JavaScript holds exactly.

BuildingKind = Literal[
    "metal_mine",
    "crystal_mine",
    "deuterium_synthesizer",
    "solar_plant",
    "metal_storage",
    "crystal_storage",
    "deuterium_tank",
    "shipyard",
    "research_lab",
]
# The order of the contract (docs/adr/0117).
BUILDING_ORDER: tuple[BuildingKind, ...] = (
    "metal_mine",
    "crystal_mine",
    "deuterium_synthesizer",
    "solar_plant",
    "metal_storage",
    "crystal_storage",
    "deuterium_tank",
    "shipyard",
    "research_lab",
)

ShipKind = Literal["small_cargo", "light_fighter"]
# The order of the contract (docs/adr/0115).
SHIP_ORDER: tuple[ShipKind, ...] = ("small_cargo", "light_fighter")

TechKind = Literal["energy_technology", "plasma_technology"]
# The order of the contract (docs/adr/0117).
TECH_ORDER: tuple[TechKind, ...] = ("energy_technology", "plasma_technology")

# Each system has this many positions (docs/adr/0118, also app/shared/orm/planets.py).
POSITIONS_PER_SYSTEM = 15
# A home planet goes to a random free position in this range.
HOME_POSITIONS: tuple[int, ...] = tuple(range(4, 13))


@dataclass(frozen=True)
class Coordinates:
    galaxy: int
    system: int
    position: int


@dataclass(frozen=True)
class Planet:
    id: UUID
    name: str
    coordinates: Coordinates


@dataclass(frozen=True)
class Resources:
    metal: int
    crystal: int
    deuterium: int


@dataclass(frozen=True)
class Energy:
    produced: int
    used: int


@dataclass(frozen=True)
class StoredVault:
    """The amounts and the time stored in the database, before production is added."""

    planet_id: UUID
    metal: int
    crystal: int
    deuterium: int
    updated_at: datetime


@dataclass(frozen=True)
class Vault:
    planet_id: UUID
    metal: int
    crystal: int
    deuterium: int
    production_per_hour: Resources
    energy: Energy
    capacity: Resources
    calculated_at: datetime


@dataclass(frozen=True)
class Construction:
    """The one running upgrade of a planet (docs/adr/0114)."""

    kind: str
    finishes_at: datetime


@dataclass(frozen=True)
class Building:
    kind: BuildingKind
    level: int
    production_per_hour: int
    energy: Energy
    upgrade_cost: Resources
    upgrade_finishes_at: datetime | None = None


@dataclass(frozen=True)
class BuildingUpgrade:
    building: Building
    vault: Vault


@dataclass(frozen=True)
class Ship:
    kind: ShipKind
    count: int
    cost: Resources
    build_seconds: int


@dataclass(frozen=True)
class StoredShipOrder:
    """The one running ship order of a planet, as stored (docs/adr/0115)."""

    kind: ShipKind
    remaining: int
    seconds_per_ship: int
    next_finishes_at: datetime


@dataclass(frozen=True)
class ShipOrder:
    kind: ShipKind
    remaining: int
    next_finishes_at: datetime
    finishes_at: datetime


@dataclass(frozen=True)
class Shipyard:
    ships: list[Ship]
    order: ShipOrder | None = None


@dataclass(frozen=True)
class ShipOrderResult:
    shipyard: Shipyard
    vault: Vault


@dataclass(frozen=True)
class StoredResearch:
    """The one running research of a player, as stored (docs/adr/0117)."""

    kind: TechKind
    planet_id: UUID
    finishes_at: datetime


@dataclass(frozen=True)
class Technology:
    kind: TechKind
    level: int
    cost: Resources
    available: bool


@dataclass(frozen=True)
class RunningResearch:
    kind: TechKind
    planet_id: UUID
    finishes_at: datetime


@dataclass(frozen=True)
class Research:
    technologies: list[Technology]
    running: RunningResearch | None = None


@dataclass(frozen=True)
class ResearchStart:
    research: Research
    vault: Vault


@dataclass(frozen=True)
class GalaxyPlanet:
    name: str
    username: str


@dataclass(frozen=True)
class GalaxyPosition:
    position: int
    planet: GalaxyPlanet | None = None


@dataclass(frozen=True)
class GalaxySystem:
    galaxy: int
    system: int
    galaxies: int
    systems_per_galaxy: int
    positions: list[GalaxyPosition]
