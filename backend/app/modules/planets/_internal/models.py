from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

MAX_AMOUNT = 9007199254740991  # 2^53 - 1, the largest integer JavaScript holds exactly.

BuildingKind = Literal["metal_mine", "crystal_mine", "deuterium_synthesizer", "solar_plant"]
# The order of the contract (docs/adr/0111, docs/adr/0112).
BUILDING_ORDER: tuple[BuildingKind, ...] = (
    "metal_mine",
    "crystal_mine",
    "deuterium_synthesizer",
    "solar_plant",
)


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
    calculated_at: datetime


@dataclass(frozen=True)
class Building:
    kind: BuildingKind
    level: int
    production_per_hour: int
    energy: Energy
    upgrade_cost: Resources


@dataclass(frozen=True)
class BuildingUpgrade:
    building: Building
    vault: Vault
