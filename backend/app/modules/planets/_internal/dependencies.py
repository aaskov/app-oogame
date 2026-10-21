from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.planets._internal.repository import PlanetRepository
from app.modules.planets._internal.service import PlanetService
from app.shared.config import Settings, get_settings
from app.shared.db import get_session


def get_current_time() -> datetime:
    """The current time. Override this in a test to set the time (docs/adr/0111)."""
    return datetime.now(UTC)


def get_planet_service(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    now: Annotated[datetime, Depends(get_current_time)],
) -> PlanetService:
    return PlanetService(PlanetRepository(session), settings, now)
