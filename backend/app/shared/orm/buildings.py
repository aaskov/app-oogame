from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.orm.base import Base

# The building kinds that exist today (docs/adr/0111, 0112, 0113, 0115). A new
# kind needs a migration that changes the check constraint.
MINE_KINDS = ("metal_mine", "crystal_mine", "deuterium_synthesizer")
STORAGE_KINDS = ("metal_storage", "crystal_storage", "deuterium_tank")
BUILDING_KINDS = (*MINE_KINDS, "solar_plant", *STORAGE_KINDS, "shipyard")


class BuildingRow(Base):
    """The level of one building on one planet. No row means level 0."""

    __tablename__ = "buildings"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('metal_mine', 'crystal_mine', 'deuterium_synthesizer', 'solar_plant', "
            "'metal_storage', 'crystal_storage', 'deuterium_tank', 'shipyard')",
            name="known_kind",
        ),
        CheckConstraint("level >= 0", name="level_not_negative"),
    )

    planet_id: Mapped[UUID] = mapped_column(
        ForeignKey("planets.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(40), primary_key=True)
    level: Mapped[int] = mapped_column(Integer, default=0)
