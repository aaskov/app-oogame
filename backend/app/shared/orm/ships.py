from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.orm.base import Base

# The ship kinds that exist today (docs/adr/0115). A new kind needs a
# migration that changes the check constraints.
SHIP_KINDS = ("small_cargo", "light_fighter")

_KINDS = ", ".join(f"'{kind}'" for kind in SHIP_KINDS)


class ShipRow(Base):
    """The number of ships of one kind on one planet. No row means 0."""

    __tablename__ = "ships"
    __table_args__ = (
        CheckConstraint(f"kind IN ({_KINDS})", name="known_kind"),
        CheckConstraint("count >= 0", name="count_not_negative"),
    )

    planet_id: Mapped[UUID] = mapped_column(
        ForeignKey("planets.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(40), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class ShipOrderRow(Base):
    """The one running ship order of a planet (docs/adr/0115). No row means none.

    The primary key is the planet, so a planet has at most one order.
    """

    __tablename__ = "ship_orders"
    __table_args__ = (
        CheckConstraint(f"kind IN ({_KINDS})", name="known_kind"),
        CheckConstraint("remaining >= 1", name="remaining_positive"),
        CheckConstraint("seconds_per_ship >= 1", name="seconds_positive"),
    )

    planet_id: Mapped[UUID] = mapped_column(
        ForeignKey("planets.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    # The ships that are not complete yet.
    remaining: Mapped[int] = mapped_column(Integer)
    # The build time of one ship, fixed when the order starts.
    seconds_per_ship: Mapped[int] = mapped_column(Integer)
    # The next ship is complete at this time.
    next_finishes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
