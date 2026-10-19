from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.orm.base import Base

# The start values of the vault of a new planet (docs/adr/0109). The OGame values.
START_METAL = 500
START_CRYSTAL = 500
START_DEUTERIUM = 0


class VaultRow(Base):
    """The resources of one planet. Each planet has exactly one vault."""

    __tablename__ = "vaults"
    __table_args__ = (
        CheckConstraint("metal >= 0", name="metal_not_negative"),
        CheckConstraint("crystal >= 0", name="crystal_not_negative"),
        CheckConstraint("deuterium >= 0", name="deuterium_not_negative"),
    )

    planet_id: Mapped[UUID] = mapped_column(
        ForeignKey("planets.id", ondelete="CASCADE"), primary_key=True
    )
    metal: Mapped[int] = mapped_column(BigInteger, default=START_METAL)
    crystal: Mapped[int] = mapped_column(BigInteger, default=START_CRYSTAL)
    deuterium: Mapped[int] = mapped_column(BigInteger, default=START_DEUTERIUM)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
