"""The SQLAlchemy table definitions (docs/adr/0104). Architect-owned (CODEOWNERS).

Repositories read and write these classes. A change here needs a new Alembic
migration in backend/migrations/.
"""

from app.shared.orm.base import Base
from app.shared.orm.buildings import BUILDING_KINDS, MINE_KINDS, STORAGE_KINDS, BuildingRow
from app.shared.orm.planets import HOME_PLANET_NAME, PlanetRow
from app.shared.orm.users import UserRow
from app.shared.orm.vaults import START_CRYSTAL, START_DEUTERIUM, START_METAL, VaultRow

__all__ = [
    "BUILDING_KINDS",
    "HOME_PLANET_NAME",
    "MINE_KINDS",
    "START_CRYSTAL",
    "START_DEUTERIUM",
    "START_METAL",
    "STORAGE_KINDS",
    "Base",
    "BuildingRow",
    "PlanetRow",
    "UserRow",
    "VaultRow",
]
