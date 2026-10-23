"""Storage buildings and capacity (docs/adr/0113)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.shared.orm.vaults import START_CRYSTAL, START_DEUTERIUM, VaultRow
from tests.test_planets import (
    new_client,
    register_and_login,
    set_building_level,
    set_clock,
    set_game_speed,
)

UNKNOWN_PLANET = "00000000-0000-0000-0000-000000000000"
BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
BUILDING_ORDER_WITH_STORAGE = [
    "metal_mine",
    "crystal_mine",
    "deuterium_synthesizer",
    "solar_plant",
    "metal_storage",
    "crystal_storage",
    "deuterium_tank",
]


def home_planet(client: TestClient, email: str = "ada@example.com") -> UUID:
    register_and_login(client, email)
    [planet] = client.get("/planets").json()
    return UUID(planet["id"])


def set_vault(
    session: Session,
    planet_id: UUID,
    *,
    metal: int | None = None,
    crystal: int | None = None,
    deuterium: int | None = None,
    updated_at: datetime | None = None,
) -> None:
    values = {
        key: value
        for key, value in {
            "metal": metal,
            "crystal": crystal,
            "deuterium": deuterium,
            "updated_at": updated_at,
        }.items()
        if value is not None
    }
    session.execute(update(VaultRow).where(VaultRow.planet_id == planet_id).values(**values))
    session.commit()


# --- Capacity values and calculations ------------------------------------------


def test_list_buildings_returns_seven_buildings_in_order(client: TestClient) -> None:
    planet_id = home_planet(client)

    response = client.get(f"/planets/{planet_id}/buildings")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 7
    assert [building["kind"] for building in body] == BUILDING_ORDER_WITH_STORAGE


def test_list_buildings_storage_at_level_0_has_zero_production_and_energy(
    client: TestClient,
) -> None:
    planet_id = home_planet(client)

    response = client.get(f"/planets/{planet_id}/buildings")

    body = response.json()
    metal_storage, crystal_storage, deuterium_tank = body[4:7]
    assert metal_storage["kind"] == "metal_storage"
    assert metal_storage["level"] == 0
    assert metal_storage["production_per_hour"] == 0
    assert metal_storage["energy"] == {"produced": 0, "used": 0}
    assert crystal_storage["kind"] == "crystal_storage"
    assert crystal_storage["production_per_hour"] == 0
    assert crystal_storage["energy"] == {"produced": 0, "used": 0}
    assert deuterium_tank["kind"] == "deuterium_tank"
    assert deuterium_tank["production_per_hour"] == 0
    assert deuterium_tank["energy"] == {"produced": 0, "used": 0}


def test_vault_capacity_at_level_0_is_10000(client: TestClient) -> None:
    planet_id = home_planet(client)

    vault = client.get(f"/planets/{planet_id}/vault").json()

    assert vault["capacity"] == {"metal": 10000, "crystal": 10000, "deuterium": 10000}


def test_vault_capacity_at_level_1_is_20000(client: TestClient, session: Session) -> None:
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "metal_storage", 1)
    set_building_level(session, planet_id, "crystal_storage", 1)
    set_building_level(session, planet_id, "deuterium_tank", 1)

    vault = client.get(f"/planets/{planet_id}/vault").json()

    assert vault["capacity"] == {"metal": 20000, "crystal": 20000, "deuterium": 20000}


def test_vault_capacity_at_level_2_is_40000(client: TestClient, session: Session) -> None:
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "metal_storage", 2)
    set_building_level(session, planet_id, "crystal_storage", 2)
    set_building_level(session, planet_id, "deuterium_tank", 2)

    vault = client.get(f"/planets/{planet_id}/vault").json()

    assert vault["capacity"] == {"metal": 40000, "crystal": 40000, "deuterium": 40000}


# --- Upgrade costs ----------------------------------------------------------


def test_metal_storage_upgrade_cost_level_0(client: TestClient) -> None:
    planet_id = home_planet(client)

    buildings = client.get(f"/planets/{planet_id}/buildings").json()

    assert buildings[4]["upgrade_cost"] == {"metal": 1000, "crystal": 0, "deuterium": 0}


def test_metal_storage_upgrade_cost_level_2(client: TestClient, session: Session) -> None:
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "metal_storage", 2)

    buildings = client.get(f"/planets/{planet_id}/buildings").json()

    assert buildings[4]["upgrade_cost"] == {"metal": 4000, "crystal": 0, "deuterium": 0}


def test_crystal_storage_upgrade_cost_level_0(client: TestClient) -> None:
    planet_id = home_planet(client)

    buildings = client.get(f"/planets/{planet_id}/buildings").json()

    assert buildings[5]["upgrade_cost"] == {"metal": 1000, "crystal": 500, "deuterium": 0}


def test_crystal_storage_upgrade_cost_level_2(client: TestClient, session: Session) -> None:
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "crystal_storage", 2)

    buildings = client.get(f"/planets/{planet_id}/buildings").json()

    assert buildings[5]["upgrade_cost"] == {"metal": 4000, "crystal": 2000, "deuterium": 0}


def test_deuterium_tank_upgrade_cost_level_0(client: TestClient) -> None:
    planet_id = home_planet(client)

    buildings = client.get(f"/planets/{planet_id}/buildings").json()

    assert buildings[6]["upgrade_cost"] == {"metal": 1000, "crystal": 1000, "deuterium": 0}


def test_deuterium_tank_upgrade_cost_level_2(client: TestClient, session: Session) -> None:
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "deuterium_tank", 2)

    buildings = client.get(f"/planets/{planet_id}/buildings").json()

    assert buildings[6]["upgrade_cost"] == {"metal": 4000, "crystal": 4000, "deuterium": 0}


# --- Production capped at capacity ------------------------------------------


def test_production_capped_at_capacity_9990_metal_and_30_per_hour_gives_10000_after_1_hour(
    session: Session,
) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_vault(
        session,
        planet_id,
        metal=9990,
        crystal=START_CRYSTAL,
        deuterium=START_DEUTERIUM,
        updated_at=BASE_TIME,
    )
    set_clock(app, BASE_TIME + timedelta(hours=1))

    vault = client.get(f"/planets/{planet_id}/vault").json()

    # At level 0 metal storage has capacity 10000. With 9990 and 30 per hour,
    # after 1 hour it should be min(10000, floor(9990 + 30)) = 10000, not 10020.
    assert vault["metal"] == 10000


def test_stored_amount_above_capacity_stays_and_does_not_grow(
    session: Session,
) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_vault(
        session,
        planet_id,
        metal=12000,
        crystal=START_CRYSTAL,
        deuterium=START_DEUTERIUM,
        updated_at=BASE_TIME,
    )
    set_clock(app, BASE_TIME + timedelta(hours=2))

    vault = client.get(f"/planets/{planet_id}/vault").json()

    # At level 0 metal storage has capacity 10000. With 12000 stored and 30 per hour,
    # after 2 hours it should stay 12000 (not grow to 12060).
    assert vault["metal"] == 12000


def test_game_speed_does_not_affect_capacity(session: Session) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_game_speed(app, 10)

    vault = client.get(f"/planets/{planet_id}/vault").json()

    # Capacity should be the same regardless of game_speed
    assert vault["capacity"] == {"metal": 10000, "crystal": 10000, "deuterium": 10000}


# --- Upgrade behavior with capacity ------------------------------------------


def test_upgrade_storage_stores_production_with_old_capacity(session: Session) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    # Start with 9990 metal at capacity 10000, then upgrade to capacity 20000
    set_vault(
        session, planet_id,
        metal=9990,
        crystal=START_CRYSTAL,
        deuterium=START_DEUTERIUM,
        updated_at=BASE_TIME,
    )
    set_clock(app, BASE_TIME + timedelta(hours=1))

    # Upgrade metal_storage from level 0 to level 1
    response = client.post(f"/planets/{planet_id}/buildings/metal_storage/upgrade")

    assert response.status_code == 200
    body = response.json()
    # Production with old capacity (10000) for 1 hour: min(10000, floor(9990 + 30)) = 10000
    # Then subtract the cost: 10000 - 1000 = 9000
    assert body["vault"]["metal"] == 9000
    assert body["vault"]["capacity"]["metal"] == 20000
    assert body["building"]["level"] == 1


def test_metal_is_full_at_capacity_upgrade_storage_1_hour_later_is_full_minus_cost_plus_production(
    session: Session,
) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_vault(
        session, planet_id,
        metal=10000,
        crystal=START_CRYSTAL,
        deuterium=START_DEUTERIUM,
        updated_at=BASE_TIME,
    )
    set_clock(app, BASE_TIME + timedelta(hours=1))

    # Upgrade metal_storage from level 0 to level 1
    upgrade = client.post(f"/planets/{planet_id}/buildings/metal_storage/upgrade")

    assert upgrade.status_code == 200
    # At capacity 10000, stored 10000 stays 10000 after 1 hour
    # Upgrade cost: 1000 metal
    # After upgrade: 10000 - 1000 = 9000
    assert upgrade.json()["vault"]["metal"] == 9000

    # Now wait 1 more hour with capacity 20000
    set_clock(app, BASE_TIME + timedelta(hours=2))
    vault = client.get(f"/planets/{planet_id}/vault").json()

    # From 9000 with 30 per hour for 1 hour: 9000 + 30 = 9030
    assert vault["metal"] == 9030


# --- Upgrade authorization --------------------------------------------------


def test_upgrade_storage_by_another_user_returns_404_and_changes_nothing(
    client: TestClient, session: Session
) -> None:
    planet_id = home_planet(client, "ada@example.com")
    before_vault = client.get(f"/planets/{planet_id}/vault").json()
    before_buildings = client.get(f"/planets/{planet_id}/buildings").json()
    unknown = client.post(f"/planets/{UNKNOWN_PLANET}/buildings/metal_storage/upgrade")

    register_and_login(client, "bob@example.com")
    other_users = client.post(f"/planets/{planet_id}/buildings/metal_storage/upgrade")

    assert other_users.status_code == 404
    assert other_users.json() == unknown.json()

    register_and_login(client, "ada@example.com")
    after_vault = client.get(f"/planets/{planet_id}/vault").json()
    assert after_vault["metal"] == before_vault["metal"]
    assert after_vault["crystal"] == before_vault["crystal"]
    assert after_vault["capacity"] == before_vault["capacity"]
    assert client.get(f"/planets/{planet_id}/buildings").json() == before_buildings


def test_upgrade_storage_returns_422_for_invalid_kind(client: TestClient) -> None:
    planet_id = home_planet(client)

    response = client.post(f"/planets/{planet_id}/buildings/invalid_storage/upgrade")

    assert response.status_code == 422


def test_upgrade_storage_returns_409_when_vault_has_too_little(
    client: TestClient, session: Session
) -> None:
    planet_id = home_planet(client)
    set_vault(session, planet_id, metal=999, crystal=0, deuterium=0)

    response = client.post(f"/planets/{planet_id}/buildings/metal_storage/upgrade")

    assert response.status_code == 409
    row = session.scalars(select(VaultRow).where(VaultRow.planet_id == planet_id)).one()
    session.refresh(row)
    assert row.metal == 999
    buildings = client.get(f"/planets/{planet_id}/buildings").json()
    assert buildings[4]["level"] == 0
