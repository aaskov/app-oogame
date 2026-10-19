from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Planet:
    id: UUID
    name: str


@dataclass(frozen=True)
class Vault:
    planet_id: UUID
    metal: int
    crystal: int
    deuterium: int
    updated_at: datetime
