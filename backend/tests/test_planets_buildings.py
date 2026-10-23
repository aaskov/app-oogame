"""Energy, buildings, and the building upgrade (docs/adr/0112)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.shared.orm.vaults import START_CRYSTAL, START_DEUTERIUM, START_METAL, VaultRow
from tests.test_planets import (
    NOT_FOUND,
    new_client,
    register_and_login,
    set_building_level,
    set_clock,
    set_game_speed,
)

UNKNOWN_PLANET = "00000000-0000-0000-0000-000000000000"
BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
BUILDING_ORDER = [
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


# --- the vault shows the energy ------------------------------------------------------


def test_read_vault_with_no_buildings_has_factor_1_and_no_energy(client: TestClient) -> None:
    planet_id = home_planet(client)

    body = client.get(f"/planets/{planet_id}/vault").json()

    assert body["energy"] == {"produced": 0, "used": 0}
    assert body["production_per_hour"] == {"metal": 30, "crystal": 15, "deuterium": 0}


def test_read_vault_metal_mine_without_a_solar_plant_gives_only_the_base_income(
    client: TestClient, session: Session
) -> None:
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "metal_mine", 1)

    vault = client.get(f"/planets/{planet_id}/vault").json()
    buildings = client.get(f"/planets/{planet_id}/buildings").json()

    assert vault["energy"] == {"produced": 0, "used": 11}
    assert vault["production_per_hour"]["metal"] == 30
    assert buildings[0]["production_per_hour"] == 0


def test_read_vault_solar_plant_1_and_metal_mine_2_gives_66_metal_per_hour(
    client: TestClient, session: Session
) -> None:
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "solar_plant", 1)
    set_building_level(session, planet_id, "metal_mine", 2)

    vault = client.get(f"/planets/{planet_id}/vault").json()
    metal_mine = client.get(f"/planets/{planet_id}/buildings").json()[0]

    assert vault["energy"] == {"produced": 22, "used": 24}
    assert metal_mine["production_per_hour"] == 66
    assert vault["production_per_hour"]["metal"] == 30 + 66


def test_read_vault_the_factor_does_not_apply_to_the_base_income(
    client: TestClient, session: Session
) -> None:
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "crystal_mine", 2)

    vault = client.get(f"/planets/{planet_id}/vault").json()

    assert vault["production_per_hour"] == {"metal": 30, "crystal": 15, "deuterium": 0}


def test_read_vault_game_speed_10_gives_10_times_the_production_and_the_same_energy(
    session: Session,
) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "solar_plant", 1)
    set_building_level(session, planet_id, "metal_mine", 1)
    normal = client.get(f"/planets/{planet_id}/vault").json()
    normal_mine = client.get(f"/planets/{planet_id}/buildings").json()[0]
    set_game_speed(app, 10)

    fast = client.get(f"/planets/{planet_id}/vault").json()
    fast_mine = client.get(f"/planets/{planet_id}/buildings").json()[0]

    assert normal_mine["production_per_hour"] == 33
    assert fast_mine["production_per_hour"] == 330
    assert fast["production_per_hour"]["metal"] == 10 * normal["production_per_hour"]["metal"]
    assert fast["energy"] == normal["energy"] == {"produced": 22, "used": 11}
    assert fast_mine["energy"] == normal_mine["energy"]


# --- GET /planets/{planet_id}/buildings ------------------------------------------------


def test_list_buildings_returns_401_without_a_session(client: TestClient) -> None:
    response = client.get(f"/planets/{UNKNOWN_PLANET}/buildings")

    assert response.status_code == 401


def test_list_buildings_returns_404_for_an_unknown_planet(client: TestClient) -> None:
    register_and_login(client, "ada@example.com")

    response = client.get(f"/planets/{UNKNOWN_PLANET}/buildings")

    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND


def test_list_buildings_returns_404_for_another_users_planet_with_the_same_detail(
    client: TestClient,
) -> None:
    planet_id = home_planet(client, "ada@example.com")
    unknown = client.get(f"/planets/{UNKNOWN_PLANET}/buildings")

    register_and_login(client, "bob@example.com")
    other_users = client.get(f"/planets/{planet_id}/buildings")

    assert other_users.status_code == 404
    assert other_users.json() == unknown.json()


def test_list_buildings_returns_the_four_buildings_in_order_at_level_0(
    client: TestClient,
) -> None:
    planet_id = home_planet(client)

    response = client.get(f"/planets/{planet_id}/buildings")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 7
    assert [building["kind"] for building in body] == BUILDING_ORDER
    assert all(building["level"] == 0 for building in body)
    assert all(building["production_per_hour"] == 0 for building in body)
    assert all(building["energy"] == {"produced": 0, "used": 0} for building in body)
    assert [building["upgrade_cost"] for building in body] == [
        {"metal": 60, "crystal": 15, "deuterium": 0},
        {"metal": 48, "crystal": 24, "deuterium": 0},
        {"metal": 225, "crystal": 75, "deuterium": 0},
        {"metal": 75, "crystal": 30, "deuterium": 0},
        {"metal": 1000, "crystal": 0, "deuterium": 0},
        {"metal": 1000, "crystal": 500, "deuterium": 0},
        {"metal": 1000, "crystal": 1000, "deuterium": 0},
    ]


def test_list_buildings_returns_the_energy_and_the_cost_at_a_level(
    client: TestClient, session: Session
) -> None:
    planet_id = home_planet(client)
    for kind in BUILDING_ORDER:
        set_building_level(session, planet_id, kind, 3)

    body = client.get(f"/planets/{planet_id}/buildings").json()

    (
        metal_mine,
        crystal_mine,
        deuterium_synthesizer,
        solar_plant,
        metal_storage,
        crystal_storage,
        deuterium_tank,
    ) = body
    assert metal_mine["energy"] == {"produced": 0, "used": 39}
    assert crystal_mine["energy"] == {"produced": 0, "used": 39}
    assert deuterium_synthesizer["energy"] == {"produced": 0, "used": 79}
    assert solar_plant["energy"] == {"produced": 79, "used": 0}
    assert solar_plant["production_per_hour"] == 0
    assert solar_plant["upgrade_cost"] == {"metal": 253, "crystal": 101, "deuterium": 0}
    # Energy 79 for a use of 157: factor 79/157. Metal: floor(119.79 * 79/157).
    assert metal_mine["production_per_hour"] == 60
    assert metal_mine["upgrade_cost"] == {"metal": 202, "crystal": 50, "deuterium": 0}
    # Storage buildings have no production or energy
    assert metal_storage["production_per_hour"] == 0
    assert metal_storage["energy"] == {"produced": 0, "used": 0}
    assert metal_storage["upgrade_cost"] == {"metal": 8000, "crystal": 0, "deuterium": 0}
    assert crystal_storage["production_per_hour"] == 0
    assert crystal_storage["energy"] == {"produced": 0, "used": 0}
    assert crystal_storage["upgrade_cost"] == {"metal": 8000, "crystal": 4000, "deuterium": 0}
    assert deuterium_tank["production_per_hour"] == 0
    assert deuterium_tank["energy"] == {"produced": 0, "used": 0}
    assert deuterium_tank["upgrade_cost"] == {"metal": 8000, "crystal": 8000, "deuterium": 0}


# --- POST /planets/{planet_id}/buildings/{kind}/upgrade ---------------------------------


def test_upgrade_building_returns_401_without_a_session(client: TestClient) -> None:
    response = client.post(f"/planets/{UNKNOWN_PLANET}/buildings/metal_mine/upgrade")

    assert response.status_code == 401


def test_upgrade_building_returns_404_for_an_unknown_planet(client: TestClient) -> None:
    register_and_login(client, "ada@example.com")

    response = client.post(f"/planets/{UNKNOWN_PLANET}/buildings/metal_mine/upgrade")

    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND


def test_upgrade_building_returns_422_for_an_unknown_kind(client: TestClient) -> None:
    planet_id = home_planet(client)

    response = client.post(f"/planets/{planet_id}/buildings/solar_satellite/upgrade")

    assert response.status_code == 422


def test_upgrade_building_by_another_user_returns_404_and_changes_nothing(
    client: TestClient, session: Session
) -> None:
    planet_id = home_planet(client, "ada@example.com")
    before_vault = client.get(f"/planets/{planet_id}/vault").json()
    before_buildings = client.get(f"/planets/{planet_id}/buildings").json()
    unknown = client.post(f"/planets/{UNKNOWN_PLANET}/buildings/solar_plant/upgrade")

    register_and_login(client, "bob@example.com")
    other_users = client.post(f"/planets/{planet_id}/buildings/solar_plant/upgrade")

    assert other_users.status_code == 404
    assert other_users.json() == unknown.json()

    register_and_login(client, "ada@example.com")
    after_vault = client.get(f"/planets/{planet_id}/vault").json()
    assert after_vault["metal"] == before_vault["metal"]
    assert after_vault["crystal"] == before_vault["crystal"]
    assert client.get(f"/planets/{planet_id}/buildings").json() == before_buildings


def test_upgrade_building_solar_plant_raises_the_level_and_the_energy(
    client: TestClient,
) -> None:
    planet_id = home_planet(client)

    response = client.post(f"/planets/{planet_id}/buildings/solar_plant/upgrade")

    assert response.status_code == 200
    body = response.json()
    assert body["building"]["kind"] == "solar_plant"
    assert body["building"]["level"] == 1
    assert body["building"]["energy"] == {"produced": 22, "used": 0}
    assert body["building"]["production_per_hour"] == 0
    assert body["building"]["upgrade_cost"] == {"metal": 112, "crystal": 45, "deuterium": 0}
    assert body["vault"]["metal"] == START_METAL - 75
    assert body["vault"]["crystal"] == START_CRYSTAL - 30
    assert body["vault"]["deuterium"] == START_DEUTERIUM
    assert body["vault"]["energy"] == {"produced": 22, "used": 0}

    buildings = client.get(f"/planets/{planet_id}/buildings").json()
    assert buildings[3]["level"] == 1
    vault = client.get(f"/planets/{planet_id}/vault").json()
    assert vault["energy"] == {"produced": 22, "used": 0}


def test_upgrade_building_returns_the_mine_with_the_factor_after_the_upgrade(
    client: TestClient, session: Session
) -> None:
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "solar_plant", 1)
    set_building_level(session, planet_id, "metal_mine", 1)

    response = client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")

    assert response.status_code == 200
    body = response.json()
    assert body["building"]["level"] == 2
    assert body["building"]["energy"] == {"produced": 0, "used": 24}
    assert body["building"]["production_per_hour"] == 66
    assert body["vault"]["energy"] == {"produced": 22, "used": 24}
    assert body["vault"]["production_per_hour"]["metal"] == 30 + 66


def test_upgrade_building_that_makes_the_energy_too_low_is_allowed(client: TestClient) -> None:
    planet_id = home_planet(client)

    response = client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")

    assert response.status_code == 200
    body = response.json()
    assert body["building"]["level"] == 1
    assert body["building"]["production_per_hour"] == 0
    assert body["vault"]["energy"] == {"produced": 0, "used": 11}
    assert body["vault"]["production_per_hour"]["metal"] == 30


def test_upgrade_building_returns_409_when_the_vault_has_too_little(
    client: TestClient, session: Session
) -> None:
    planet_id = home_planet(client)
    set_vault(session, planet_id, metal=74, crystal=1000, deuterium=0)

    response = client.post(f"/planets/{planet_id}/buildings/solar_plant/upgrade")

    assert response.status_code == 409
    assert "detail" in response.json()
    row = session.scalars(select(VaultRow).where(VaultRow.planet_id == planet_id)).one()
    session.refresh(row)
    assert (row.metal, row.crystal, row.deuterium) == (74, 1000, 0)
    buildings = client.get(f"/planets/{planet_id}/buildings").json()
    assert buildings[3]["level"] == 0


def test_upgrade_building_stores_the_production_with_the_old_factor(session: Session) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    # Solar plant 1 makes 22 and metal mine 1 uses 11: factor 1, 63 metal and 15 crystal per hour.
    set_building_level(session, planet_id, "solar_plant", 1)
    set_building_level(session, planet_id, "metal_mine", 1)
    set_vault(session, planet_id, metal=1000, crystal=1000, deuterium=0, updated_at=BASE_TIME)

    # 2 hours at factor 1, then metal mine 2 uses 24 and the factor is 22/24.
    set_clock(app, BASE_TIME + timedelta(hours=2))
    upgrade = client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")

    assert upgrade.status_code == 200
    assert upgrade.json()["vault"]["metal"] == 1000 + 2 * 63 - 90
    assert upgrade.json()["vault"]["crystal"] == 1000 + 2 * 15 - 22

    # 1 more hour at the new production: 30 base + 66 from the mine.
    set_clock(app, BASE_TIME + timedelta(hours=3))
    vault = client.get(f"/planets/{planet_id}/vault").json()

    assert vault["metal"] == 1000 + 2 * 63 - 90 + 1 * 96
    assert vault["crystal"] == 1000 + 2 * 15 - 22 + 1 * 15
