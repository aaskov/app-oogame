from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.health._internal.schemas import Health
from app.modules.health._internal.service import HealthService, get_health_service

router = APIRouter(tags=["health"])


@router.get("/health")
def read_health(service: Annotated[HealthService, Depends(get_health_service)]) -> Health:
    return service.get_health()
