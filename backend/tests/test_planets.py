from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.main import create_app
from app.modules.planets._internal.dependencies import get_current_time
from app.shared.config import get_settings
from app.shared.db import get_session
from app.shared.orm.buildings import BuildingRow
from app.shared.orm.planets import PlanetRow
from app.shared.orm.users import UserRow
from app.shared.orm.vaults import START_CRYSTAL, START_DEUTERIUM, START_METAL, VaultRow

NOT_FOUND = "Planet not found"


def register_and_login(client: TestClient, email: str) -> None:
    client.post("/auth/register", json={"email": email, "password": "correct horse"})
    client.post("/auth/login", json={"email": email, "password": "correct horse"})


def new_client(session: Session) -> tuple[FastAPI, TestClient]:
    """An app bound to the test's session, so a test can also override the clock
    or the settings without touching tests/conftest.py."""
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    return app, TestClient(app)


def set_clock(app: FastAPI, when: datetime) -> None:
    app.dependency_overrides[get_current_time] = lambda: when


def set_game_speed(app: FastAPI, game_speed: float) -> None:
    settings = get_settings().model_copy(update={"game_speed": game_speed})
    app.dependency_overrides[get_settings] = lambda: settings


def planets_of(email: str):
    # Other test runs can commit rows at the same time. Read only this user's rows.
    return select(PlanetRow).join(UserRow, UserRow.id == PlanetRow.user_id).where(
        UserRow.email == email
    )


def set_building_level(session: Session, planet_id: UUID, kind: str, level: int) -> None:
    session.add(BuildingRow(planet_id=planet_id, kind=kind, level=level))
    session.commit()


# --- GET /planets -------------------------------------------------------------


def test_list_planets_returns_401_without_a_session(client: TestClient) -> None:
    response = client.get("/planets")

    assert response.status_code == 401


def test_list_planets_creates_a_home_planet_on_the_first_call(client: TestClient) -> None:
    register_and_login(client, "ada@example.com")

    response = client.get("/planets")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert UUID(body[0]["id"])
    assert body[0]["name"] == "Homeworld"


def test_list_planets_creates_the_home_vault_with_the_start_values(
    client: TestClient, session: Session
) -> None:
    register_and_login(client, "ada@example.com")

    client.get("/planets")

    row = session.scalars(planets_of("ada@example.com")).one()
    assert row.is_home is True
    vault = client.get(f"/planets/{row.id}/vault").json()
    assert vault["metal"] == START_METAL
    assert vault["crystal"] == START_CRYSTAL
    assert vault["deuterium"] == START_DEUTERIUM


def test_list_planets_two_first_calls_create_exactly_one_home_planet(
    client: TestClient, session: Session
) -> None:
    register_and_login(client, "ada@example.com")

    first = client.get("/planets").json()
    second = client.get("/planets").json()

    assert first == second
    rows = session.scalars(planets_of("ada@example.com")).all()
    assert len(rows) == 1
    assert rows[0].is_home is True


def test_list_planets_returns_planets_oldest_first(client: TestClient, session: Session) -> None:
    register_and_login(client, "ada@example.com")
    client.get("/planets")
    home = session.scalars(planets_of("ada@example.com")).one()
    other = PlanetRow(user_id=home.user_id, name="Colony", is_home=False)
    session.add(other)
    session.commit()

    response = client.get("/planets")

    body = response.json()
    assert [planet["id"] for planet in body] == [str(home.id), str(other.id)]


def test_list_planets_does_not_list_another_users_planets(client: TestClient) -> None:
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()

    register_and_login(client, "bob@example.com")
    body = client.get("/planets").json()

    assert all(other["id"] != planet["id"] for other in body)


# --- GET /planets/{planet_id}/vault --------------------------------------------


def test_read_vault_returns_401_without_a_session(client: TestClient) -> None:
    response = client.get("/planets/00000000-0000-0000-0000-000000000000/vault")

    assert response.status_code == 401


def test_read_vault_returns_404_for_an_unknown_planet(client: TestClient) -> None:
    register_and_login(client, "ada@example.com")

    response = client.get("/planets/00000000-0000-0000-0000-000000000000/vault")

    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND


def test_read_vault_returns_404_for_another_users_planet_with_the_same_detail(
    client: TestClient,
) -> None:
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()
    unknown = client.get("/planets/00000000-0000-0000-0000-000000000000/vault")

    register_and_login(client, "bob@example.com")
    other_users = client.get(f"/planets/{planet['id']}/vault")

    assert other_users.status_code == 404
    assert other_users.json() == unknown.json()


def test_read_vault_at_level_0_after_two_hours(session: Session) -> None:
    app, client = new_client(session)
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()
    planet_id = UUID(planet["id"])
    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    session.execute(
        update(VaultRow).where(VaultRow.planet_id == planet_id).values(updated_at=base_time)
    )
    session.commit()
    set_clock(app, base_time + timedelta(hours=2))

    response = client.get(f"/planets/{planet_id}/vault")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "planet_id",
        "metal",
        "crystal",
        "deuterium",
        "production_per_hour",
        "energy",
        "capacity",
        "calculated_at",
    }
    assert body["metal"] == START_METAL + 60
    assert body["crystal"] == START_CRYSTAL + 30
    assert body["deuterium"] == START_DEUTERIUM
    assert body["production_per_hour"] == {"metal": 30, "crystal": 15, "deuterium": 0}
    assert datetime.fromisoformat(body["calculated_at"]) == base_time + timedelta(hours=2)


def test_read_vault_counts_no_production_for_a_clock_before_the_stored_time(
    session: Session,
) -> None:
    # A request can read its time, then wait for an upgrade that stores a later
    # time (docs/adr/0111). Negative hours must count as 0, not below 0.
    app, client = new_client(session)
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()
    planet_id = UUID(planet["id"])
    stored_at = datetime(2026, 1, 1, tzinfo=UTC)
    session.execute(
        update(VaultRow)
        .where(VaultRow.planet_id == planet_id)
        .values(metal=0, crystal=0, deuterium=0, updated_at=stored_at)
    )
    session.commit()
    set_clock(app, stored_at - timedelta(minutes=1))

    response = client.get(f"/planets/{planet_id}/vault")

    assert response.status_code == 200
    assert (response.json()["metal"], response.json()["crystal"]) == (0, 0)


def test_upgrade_building_does_not_store_a_time_before_the_stored_time(session: Session) -> None:
    app, client = new_client(session)
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()
    planet_id = UUID(planet["id"])
    stored_at = datetime(2026, 1, 1, tzinfo=UTC)
    session.execute(
        update(VaultRow).where(VaultRow.planet_id == planet_id).values(updated_at=stored_at)
    )
    session.commit()
    set_clock(app, stored_at - timedelta(minutes=1))

    response = client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")

    assert response.status_code == 200
    row = session.scalars(select(VaultRow).where(VaultRow.planet_id == planet_id)).one()
    session.refresh(row)
    assert row.updated_at == stored_at


def test_read_vault_at_level_3_after_two_hours(session: Session) -> None:
    app, client = new_client(session)
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()
    planet_id = UUID(planet["id"])
    # Mines of level 3 use 157 energy. A solar plant of level 5 makes 161: factor 1.
    for kind in ("metal_mine", "crystal_mine", "deuterium_synthesizer"):
        set_building_level(session, planet_id, kind, 3)
    set_building_level(session, planet_id, "solar_plant", 5)
    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    session.execute(
        update(VaultRow).where(VaultRow.planet_id == planet_id).values(updated_at=base_time)
    )
    session.commit()
    set_clock(app, base_time + timedelta(hours=2))

    response = client.get(f"/planets/{planet_id}/vault")

    assert response.status_code == 200
    body = response.json()
    assert body["production_per_hour"] == {"metal": 149, "crystal": 94, "deuterium": 39}
    assert body["metal"] == START_METAL + 2 * 149
    assert body["crystal"] == START_CRYSTAL + 2 * 94
    assert body["deuterium"] == START_DEUTERIUM + 2 * 39


def test_read_vault_game_speed_10_gives_10_times_the_production(session: Session) -> None:
    app, client = new_client(session)
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()
    set_game_speed(app, 10)

    response = client.get(f"/planets/{planet['id']}/vault")

    assert response.status_code == 200
    assert response.json()["production_per_hour"] == {
        "metal": 300,
        "crystal": 150,
        "deuterium": 0,
    }


def test_read_vault_caps_the_amount_at_the_maximum(session: Session) -> None:
    from app.modules.planets._internal.schemas import MAX_AMOUNT

    app, client = new_client(session)
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()
    planet_id = UUID(planet["id"])
    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    # Start at capacity 10000 and produce for 1000 hours. This would exceed MAX_AMOUNT.
    session.execute(
        update(VaultRow)
        .where(VaultRow.planet_id == planet_id)
        .values(metal=MAX_AMOUNT - 100, updated_at=base_time)
    )
    session.commit()
    set_clock(app, base_time + timedelta(hours=1))

    response = client.get(f"/planets/{planet_id}/vault")

    assert response.status_code == 200
    # Already above capacity 10000, so amount stays the same (docs/adr/0113)
    assert response.json()["metal"] == MAX_AMOUNT - 100


# --- GET /planets/{planet_id}/buildings and the upgrade -----------------------
# The other buildings tests are in test_planets_buildings.py.


def test_list_buildings_returns_the_production_and_the_cost_at_a_level(
    client: TestClient, session: Session
) -> None:
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()
    set_building_level(session, UUID(planet["id"]), "metal_mine", 3)
    set_building_level(session, UUID(planet["id"]), "solar_plant", 2)

    response = client.get(f"/planets/{planet['id']}/buildings")

    assert response.status_code == 200
    [metal_mine, *_] = response.json()
    assert metal_mine["level"] == 3
    assert metal_mine["production_per_hour"] == 119
    assert metal_mine["upgrade_cost"] == {"metal": 202, "crystal": 50, "deuterium": 0}


def test_upgrade_building_raises_the_level_and_subtracts_the_cost(client: TestClient) -> None:
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()

    response = client.post(f"/planets/{planet['id']}/buildings/metal_mine/upgrade")

    assert response.status_code == 200
    body = response.json()
    assert body["building"]["kind"] == "metal_mine"
    assert body["building"]["level"] == 1
    assert body["vault"]["metal"] == START_METAL - 60
    assert body["vault"]["crystal"] == START_CRYSTAL - 15
    assert body["vault"]["deuterium"] == START_DEUTERIUM

    buildings = client.get(f"/planets/{planet['id']}/buildings").json()
    assert buildings[0]["level"] == 1
    vault = client.get(f"/planets/{planet['id']}/vault").json()
    assert vault["metal"] == START_METAL - 60
    assert vault["crystal"] == START_CRYSTAL - 15
