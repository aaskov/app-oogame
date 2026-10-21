from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MAX_AMOUNT = 9007199254740991  # 2^53 - 1, the largest integer JavaScript holds exactly.

Amount = Annotated[int, Field(ge=0, le=MAX_AMOUNT)]


class PlanetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str = Field(max_length=40)


class VaultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    planet_id: UUID
    metal: Amount
    crystal: Amount
    deuterium: Amount
    updated_at: datetime


class ErrorOut(BaseModel):
    detail: str
