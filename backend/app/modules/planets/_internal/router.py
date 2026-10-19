from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.public_api import get_current_user_id
from app.modules.planets._internal.dependencies import get_planet_service
from app.modules.planets._internal.models import Planet, Vault
from app.modules.planets._internal.schemas import ErrorOut, PlanetOut, VaultOut, VaultUpdate
from app.modules.planets._internal.service import PlanetService

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
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
def read_vault(planet_id: UUID, user_id: UserIdDep, service: ServiceDep) -> Vault:
    vault = service.read_vault(planet_id, user_id)
    if vault is None:
        raise HTTPException(status_code=404, detail=PLANET_NOT_FOUND)
    return vault


@router.patch(
    "/{planet_id}/vault",
    operation_id="update_vault",
    response_model=VaultOut,
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}, 422: {}},
)
def update_vault(
    planet_id: UUID, body: VaultUpdate, user_id: UserIdDep, service: ServiceDep
) -> Vault:
    vault = service.update_vault(
        planet_id, user_id, metal=body.metal, crystal=body.crystal, deuterium=body.deuterium
    )
    if vault is None:
        raise HTTPException(status_code=404, detail=PLANET_NOT_FOUND)
    return vault
