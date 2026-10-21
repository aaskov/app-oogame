"""The SQLAlchemy table definitions (docs/adr/0104). Architect-owned (CODEOWNERS).

Repositories read and write these classes. A change here needs a new Alembic
migration in backend/migrations/.
"""

from app.shared.orm.base import Base
from app.shared.orm.buildings import MINE_KINDS, BuildingRow
from app.shared.orm.planets import HOME_PLANET_NAME, PlanetRow
from app.shared.orm.users import UserRow
from app.shared.orm.vaults import START_CRYSTAL, START_DEUTERIUM, START_METAL, VaultRow

__all__ = [
    "HOME_PLANET_NAME",
    "MINE_KINDS",
    "START_CRYSTAL",
    "START_DEUTERIUM",
    "START_METAL",
    "Base",
    "BuildingRow",
    "PlanetRow",
    "UserRow",
    "VaultRow",
]
