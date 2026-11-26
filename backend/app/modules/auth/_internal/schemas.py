from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

Username = Annotated[
    str, StringConstraints(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
]


class Credentials(BaseModel):
    email: Annotated[EmailStr, StringConstraints(max_length=320)]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class Registration(BaseModel):
    email: Annotated[EmailStr, StringConstraints(max_length=320)]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]
    username: Username


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    username: Username


class ErrorOut(BaseModel):
    detail: str
