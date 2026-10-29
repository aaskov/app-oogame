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
]
# The order of the contract (docs/adr/0113).
BUILDING_ORDER: tuple[BuildingKind, ...] = (
    "metal_mine",
    "crystal_mine",
    "deuterium_synthesizer",
    "solar_plant",
    "metal_storage",
    "crystal_storage",
    "deuterium_tank",
    "shipyard",
)

ShipKind = Literal["small_cargo", "light_fighter"]
# The order of the contract (docs/adr/0115).
SHIP_ORDER: tuple[ShipKind, ...] = ("small_cargo", "light_fighter")


@dataclass(frozen=True)
class Planet:
    id: UUID
    name: str


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
