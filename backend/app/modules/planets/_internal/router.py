from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.public_api import get_current_user_id
from app.modules.planets._internal.dependencies import get_planet_service
from app.modules.planets._internal.models import Mine, MineKind, MineUpgrade, Planet, Vault
from app.modules.planets._internal.schemas import (
    ErrorOut,
    MineOut,
    MineUpgradeOut,
    PlanetOut,
    VaultOut,
)
from app.modules.planets._internal.service import InsufficientResourcesError, PlanetService

router = APIRouter(prefix="/planets", tags=["planets"])

ServiceDep = Annotated[PlanetService, Depends(get_planet_service)]
UserIdDep = Annotated[UUID, Depends(get_current_user_id)]

PLANET_NOT_FOUND = "Planet not found"


@router.get(
    "",
    operation_id="list_planets",
    response_model=list[PlanetOut],
    responses={401: {"model": ErrorOut}},
)
def list_planets(user_id: UserIdDep, service: ServiceDep) -> list[Planet]:
    return service.list_planets(user_id)


@router.get(
    "/{planet_id}/vault",
    operation_id="read_vault",
    response_model=VaultOut,
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}, 422: {}},
)
def read_vault(planet_id: UUID, user_id: UserIdDep, service: ServiceDep) -> Vault:
    vault = service.read_vault(planet_id, user_id)
    if vault is None:
        raise HTTPException(status_code=404, detail=PLANET_NOT_FOUND)
    return vault


@router.get(
    "/{planet_id}/mines",
    operation_id="list_mines",
    response_model=list[MineOut],
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}, 422: {}},
)
def list_mines(planet_id: UUID, user_id: UserIdDep, service: ServiceDep) -> list[Mine]:
    mines = service.list_mines(planet_id, user_id)
    if mines is None:
        raise HTTPException(status_code=404, detail=PLANET_NOT_FOUND)
    return mines


@router.post(
    "/{planet_id}/mines/{mine}/upgrade",
    operation_id="upgrade_mine",
    response_model=MineUpgradeOut,
    responses={
        401: {"model": ErrorOut},
        404: {"model": ErrorOut},
        409: {"model": ErrorOut},
        422: {},
    },
)
def upgrade_mine(
    planet_id: UUID, mine: MineKind, user_id: UserIdDep, service: ServiceDep
) -> MineUpgrade:
    try:
        result = service.upgrade_mine(planet_id, user_id, mine)
    except InsufficientResourcesError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail=PLANET_NOT_FOUND)
    return result
