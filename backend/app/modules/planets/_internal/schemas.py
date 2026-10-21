from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MAX_AMOUNT = 9007199254740991  # 2^53 - 1, the largest integer JavaScript holds exactly.

Amount = Annotated[int, Field(ge=0, le=MAX_AMOUNT)]
MineKind = Literal["metal_mine", "crystal_mine", "deuterium_synthesizer"]


class PlanetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str = Field(max_length=40)


class ResourcesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metal: Amount
    crystal: Amount
    deuterium: Amount


class VaultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    planet_id: UUID
    metal: Amount
    crystal: Amount
    deuterium: Amount
    production_per_hour: ResourcesOut
    calculated_at: datetime


class MineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: MineKind
    level: int = Field(ge=0)
    production_per_hour: Amount
    upgrade_cost: ResourcesOut


class MineUpgradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mine: MineOut
    vault: VaultOut


class ErrorOut(BaseModel):
    detail: str
