from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.orm.planets import PlanetRow
from app.shared.orm.vaults import START_CRYSTAL, START_DEUTERIUM, START_METAL

NOT_FOUND = "Planet not found"


def register_and_login(client: TestClient, email: str) -> None:
    client.post("/auth/register", json={"email": email, "password": "correct horse"})
    client.post("/auth/login", json={"email": email, "password": "correct horse"})


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

    row = session.scalars(select(PlanetRow)).one()
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
    rows = session.scalars(select(PlanetRow)).all()
    assert len(rows) == 1
    assert rows[0].is_home is True


def test_list_planets_returns_planets_oldest_first(
    client: TestClient, session: Session
) -> None:
    register_and_login(client, "ada@example.com")
    client.get("/planets")
    home = session.scalars(select(PlanetRow)).one()
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


def test_read_vault_returns_the_vault(client: TestClient) -> None:
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()

    response = client.get(f"/planets/{planet['id']}/vault")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"planet_id", "metal", "crystal", "deuterium", "updated_at"}
    assert body["planet_id"] == planet["id"]
    assert body["metal"] == START_METAL
    assert body["crystal"] == START_CRYSTAL
    assert body["deuterium"] == START_DEUTERIUM


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


# --- PATCH /planets/{planet_id}/vault ------------------------------------------
