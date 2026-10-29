from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.public_api import get_current_user_id
from app.modules.planets._internal.dependencies import get_planet_service
from app.modules.planets._internal.models import (
    Building,
    BuildingKind,
    BuildingUpgrade,
    Planet,
    ShipKind,
    ShipOrderResult,
    Shipyard,
    Vault,
)
from app.modules.planets._internal.schemas import (
    BuildingOut,
    BuildingUpgradeOut,
    ErrorOut,
    PlanetOut,
    ShipOrderRequest,
    ShipOrderResultOut,
    ShipyardOut,
    VaultOut,
)
from app.modules.planets._internal.service import (
    InsufficientResourcesError,
    NoShipyardError,
    PlanetService,
    ShipOrderRunningError,
    UpgradeRunningError,
)

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
    "/{planet_id}/buildings",
    operation_id="list_buildings",
    response_model=list[BuildingOut],
    response_model_exclude_none=True,
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}, 422: {}},
)
def list_buildings(planet_id: UUID, user_id: UserIdDep, service: ServiceDep) -> list[Building]:
    buildings = service.list_buildings(planet_id, user_id)
    if buildings is None:
        raise HTTPException(status_code=404, detail=PLANET_NOT_FOUND)
    return buildings


@router.post(
    "/{planet_id}/buildings/{kind}/upgrade",
    operation_id="upgrade_building",
    response_model=BuildingUpgradeOut,
    response_model_exclude_none=True,
    responses={
        401: {"model": ErrorOut},
        404: {"model": ErrorOut},
        409: {"model": ErrorOut},
        422: {},
    },
)
def upgrade_building(
    planet_id: UUID, kind: BuildingKind, user_id: UserIdDep, service: ServiceDep
) -> BuildingUpgrade:
    try:
        result = service.upgrade_building(planet_id, user_id, kind)
    except (InsufficientResourcesError, UpgradeRunningError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail=PLANET_NOT_FOUND)
    return result


@router.get(
    "/{planet_id}/ships",
    operation_id="read_shipyard",
    response_model=ShipyardOut,
    response_model_exclude_none=True,
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}, 422: {}},
)
def read_shipyard(planet_id: UUID, user_id: UserIdDep, service: ServiceDep) -> Shipyard:
    shipyard = service.read_shipyard(planet_id, user_id)
    if shipyard is None:
        raise HTTPException(status_code=404, detail=PLANET_NOT_FOUND)
    return shipyard


@router.post(
    "/{planet_id}/ships/{kind}/order",
    operation_id="order_ships",
    response_model=ShipOrderResultOut,
    response_model_exclude_none=True,
    responses={
        401: {"model": ErrorOut},
        404: {"model": ErrorOut},
        409: {"model": ErrorOut},
        422: {},
    },
)
def order_ships(
    planet_id: UUID,
    kind: ShipKind,
    body: ShipOrderRequest,
    user_id: UserIdDep,
    service: ServiceDep,
) -> ShipOrderResult:
    try:
        result = service.order_ships(planet_id, user_id, kind, body.count)
    except (NoShipyardError, ShipOrderRunningError, InsufficientResourcesError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail=PLANET_NOT_FOUND)
    return result
