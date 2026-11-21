from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.orm.base import Base

# The technologies that exist today (docs/adr/0117). A new kind needs a
# migration that changes the check constraints.
TECH_KINDS = ("energy_technology", "plasma_technology")

_KINDS = ", ".join(f"'{kind}'" for kind in TECH_KINDS)


class TechnologyRow(Base):
    """The level of one technology of one player. No row means level 0.

    A technology belongs to the player, so it counts on each planet.
    """

    __tablename__ = "technologies"
    __table_args__ = (
        CheckConstraint(f"kind IN ({_KINDS})", name="known_kind"),
        CheckConstraint("level >= 0", name="level_not_negative"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(40), primary_key=True)
    level: Mapped[int] = mapped_column(Integer, default=0)


class ResearchRow(Base):
    """The one running research of a player (docs/adr/0117). No row means none.

    The primary key is the player, so a player has at most one research.
    """

    __tablename__ = "researches"
    __table_args__ = (CheckConstraint(f"kind IN ({_KINDS})", name="known_kind"),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    # The planet that paid, and whose lab does the research.
    planet_id: Mapped[UUID] = mapped_column(ForeignKey("planets.id", ondelete="CASCADE"))
    # The technology gets the new level at this time.
    finishes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
