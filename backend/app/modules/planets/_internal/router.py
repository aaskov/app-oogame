from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path

from app.modules.auth.public_api import get_current_user_id
from app.modules.planets._internal.dependencies import get_planet_service
from app.modules.planets._internal.models import (
    Building,
    BuildingKind,
    BuildingUpgrade,
    GalaxySystem,
    Planet,
    Research,
    ResearchStart,
    ShipKind,
    ShipOrderResult,
    Shipyard,
    TechKind,
    Vault,
)
from app.modules.planets._internal.schemas import (
    BuildingOut,
    BuildingUpgradeOut,
    ErrorOut,
    GalaxySystemOut,
    PlanetOut,
    ResearchOut,
    ResearchStartOut,
    ShipOrderRequest,
    ShipOrderResultOut,
    ShipyardOut,
    VaultOut,
)
from app.modules.planets._internal.service import (
    InsufficientResourcesError,
    NoFreePositionError,
    NoLabError,
    NoShipyardError,
    PlanetService,
    ResearchRunningError,
    ShipOrderRunningError,
    TechnologyNotAvailableError,
    UpgradeRunningError,
)

router = APIRouter()
planets_router = APIRouter(prefix="/planets", tags=["planets"])
research_router = APIRouter(tags=["research"])
galaxy_router = APIRouter(tags=["galaxy"])

ServiceDep = Annotated[PlanetService, Depends(get_planet_service)]
UserIdDep = Annotated[UUID, Depends(get_current_user_id)]

PLANET_NOT_FOUND = "Planet not found"


@planets_router.get(
    "",
    operation_id="list_planets",
    response_model=list[PlanetOut],
    responses={401: {"model": ErrorOut}, 503: {"model": ErrorOut}},
)
def list_planets(user_id: UserIdDep, service: ServiceDep) -> list[Planet]:
    try:
        return service.list_planets(user_id)
    except NoFreePositionError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@planets_router.get(
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


@planets_router.get(
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


@planets_router.post(
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


@planets_router.get(
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


@planets_router.post(
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


@planets_router.post(
    "/{planet_id}/research/{kind}/start",
    operation_id="start_research",
    response_model=ResearchStartOut,
    response_model_exclude_none=True,
    responses={
        401: {"model": ErrorOut},
        404: {"model": ErrorOut},
        409: {"model": ErrorOut},
        422: {},
    },
)
def start_research(
    planet_id: UUID, kind: TechKind, user_id: UserIdDep, service: ServiceDep
) -> ResearchStart:
    try:
        result = service.start_research(planet_id, user_id, kind)
    except (
        NoLabError,
        ResearchRunningError,
        TechnologyNotAvailableError,
        InsufficientResourcesError,
    ) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail=PLANET_NOT_FOUND)
    return result


@research_router.get(
    "/research",
    operation_id="read_research",
    response_model=ResearchOut,
    response_model_exclude_none=True,
    responses={401: {"model": ErrorOut}},
)
def read_research(user_id: UserIdDep, service: ServiceDep) -> Research:
    return service.read_research(user_id)


@galaxy_router.get(
    "/galaxy/{galaxy}/{system}",
    operation_id="read_galaxy_system",
    response_model=GalaxySystemOut,
    response_model_exclude_none=True,
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}, 422: {}},
)
def read_galaxy_system(
    galaxy: Annotated[int, Path(ge=1)],
    system: Annotated[int, Path(ge=1)],
    user_id: UserIdDep,
    service: ServiceDep,
) -> GalaxySystem:
    result = service.read_galaxy_system(galaxy, system)
    if result is None:
        raise HTTPException(status_code=404, detail="Galaxy or system not found")
    return result


router.include_router(planets_router)
router.include_router(research_router)
router.include_router(galaxy_router)
