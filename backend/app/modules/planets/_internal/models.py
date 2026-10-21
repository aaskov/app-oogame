from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

MAX_AMOUNT = 9007199254740991  # 2^53 - 1, the largest integer JavaScript holds exactly.

MineKind = Literal["metal_mine", "crystal_mine", "deuterium_synthesizer"]
# The order of the contract (docs/adr/0111).
MINE_ORDER: tuple[MineKind, ...] = ("metal_mine", "crystal_mine", "deuterium_synthesizer")


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
    calculated_at: datetime


@dataclass(frozen=True)
class Mine:
    kind: MineKind
    level: int
    production_per_hour: int
    upgrade_cost: Resources


@dataclass(frozen=True)
class MineUpgrade:
    mine: Mine
    vault: Vault
