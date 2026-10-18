from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    password_hash: str


class EmailTakenError(Exception):
    pass
