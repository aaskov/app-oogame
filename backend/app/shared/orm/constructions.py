from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.orm.base import Base
from app.shared.orm.buildings import BUILDING_KINDS

_KINDS = ", ".join(f"'{kind}'" for kind in BUILDING_KINDS)


class ConstructionRow(Base):
    """The one running upgrade of a planet (docs/adr/0114). No row means none.

    The primary key is the planet, so a planet has at most one upgrade.
    """

    __tablename__ = "constructions"
    __table_args__ = (CheckConstraint(f"kind IN ({_KINDS})", name="known_kind"),)

    planet_id: Mapped[UUID] = mapped_column(
        ForeignKey("planets.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    # The building gets the new level at this time.
    finishes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
