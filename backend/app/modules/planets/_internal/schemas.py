from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.json_schema import SkipJsonSchema

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


class VaultUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # A field can be left out (None: it does not change), but a client cannot
    # send null (docs/adr/0110). SkipJsonSchema keeps null out of the schema.
    metal: Amount | SkipJsonSchema[None] = None
    crystal: Amount | SkipJsonSchema[None] = None
    deuterium: Amount | SkipJsonSchema[None] = None

    @field_validator("metal", "crystal", "deuterium", mode="before")
    @classmethod
    def reject_null(cls, value: object) -> object:
        # Pydantic runs this only for a value in the request, not for the default.
        if value is None:
            raise ValueError("must be an integer, not null")
        return value


class ErrorOut(BaseModel):
    detail: str
