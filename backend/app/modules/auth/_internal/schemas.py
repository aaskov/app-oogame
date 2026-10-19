from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints


class Credentials(BaseModel):
    email: Annotated[EmailStr, StringConstraints(max_length=320)]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr


class ErrorOut(BaseModel):
    detail: str
