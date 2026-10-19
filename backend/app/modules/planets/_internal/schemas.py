from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MAX_AMOUNT = 9007199254740991  # 2^53 - 1, the largest integer JavaScript holds exactly.


class PlanetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class VaultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    planet_id: UUID
    metal: int
    crystal: int
    deuterium: int
    updated_at: datetime


class VaultUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metal: int | None = Field(default=None, ge=0, le=MAX_AMOUNT)
    crystal: int | None = Field(default=None, ge=0, le=MAX_AMOUNT)
    deuterium: int | None = Field(default=None, ge=0, le=MAX_AMOUNT)


class ErrorOut(BaseModel):
    detail: str
