from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.orm.base import Base

# The planet that each user gets at the first GET /planets (docs/adr/0109).
HOME_PLANET_NAME = "Homeworld"
# Each system has this many positions (docs/adr/0118).
POSITIONS_PER_SYSTEM = 15


class PlanetRow(Base):
    __tablename__ = "planets"
    __table_args__ = (
        # At most one home planet for each user. Two first requests at the
        # same time cannot create two home planets.
        Index(
            "ix_planets_one_home_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_home"),
        ),
        # One planet for each position (docs/adr/0118). The coordinates are
        # nullable until the backend sets them for each new planet.
        UniqueConstraint("galaxy", "system", "position", name="uq_planets_coordinates"),
        CheckConstraint("galaxy >= 1", name="galaxy_positive"),
        CheckConstraint("system >= 1", name="system_positive"),
        CheckConstraint("position BETWEEN 1 AND 15", name="position_in_system"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    is_home: Mapped[bool] = mapped_column(Boolean, default=False)
    galaxy: Mapped[int | None] = mapped_column(Integer)
    system: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
