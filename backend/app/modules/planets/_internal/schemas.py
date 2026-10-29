from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

MAX_AMOUNT = 9007199254740991  # 2^53 - 1, the largest integer JavaScript holds exactly.

Amount = Annotated[int, Field(ge=0, le=MAX_AMOUNT)]
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
ShipKind = Literal["small_cargo", "light_fighter"]


class PlanetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str = Field(max_length=40)


class ResourcesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metal: Amount
    crystal: Amount
    deuterium: Amount


class EnergyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    produced: int = Field(ge=0)
    used: int = Field(ge=0)


class VaultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    planet_id: UUID
    metal: Amount
    crystal: Amount
    deuterium: Amount
    production_per_hour: ResourcesOut
    energy: EnergyOut
    capacity: ResourcesOut
    calculated_at: datetime


class BuildingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: BuildingKind
    level: int = Field(ge=0)
    production_per_hour: Amount
    energy: EnergyOut
    upgrade_cost: ResourcesOut
    # Absent, not null, without a running upgrade (docs/adr/0110, docs/adr/0114).
    upgrade_finishes_at: datetime | SkipJsonSchema[None] = None


class BuildingUpgradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building: BuildingOut
    vault: VaultOut


class ShipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: ShipKind
    count: int = Field(ge=0)
    cost: ResourcesOut
    build_seconds: int = Field(ge=1)


class ShipOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: ShipKind
    remaining: int = Field(ge=1)
    next_finishes_at: datetime
    finishes_at: datetime


class ShipyardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ships: list[ShipOut]
    # Absent, not null, without a running order (docs/adr/0110, docs/adr/0115).
    order: ShipOrderOut | SkipJsonSchema[None] = None


class ShipOrderRequest(BaseModel):
    count: int = Field(ge=1, le=1000)


class ShipOrderResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shipyard: ShipyardOut
    vault: VaultOut


class ErrorOut(BaseModel):
    detail: str
