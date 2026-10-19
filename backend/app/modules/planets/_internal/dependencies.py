from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.planets._internal.repository import PlanetRepository
from app.modules.planets._internal.service import PlanetService
from app.shared.db import get_session


def get_planet_service(session: Annotated[Session, Depends(get_session)]) -> PlanetService:
    return PlanetService(PlanetRepository(session))
