"""Coordinates for each planet and the galaxy system view (docs/adr/0118)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.shared.config import get_settings
from app.shared.orm.planets import PlanetRow
from app.shared.orm.users import UserRow
from tests.test_planets import new_client, register_and_login


def set_universe(app: FastAPI, galaxies: int, systems_per_galaxy: int) -> None:
    settings = get_settings().model_copy(
        update={"galaxies": galaxies, "systems_per_galaxy": systems_per_galaxy}
    )
    app.dependency_overrides[get_settings] = lambda: settings


def fill_position(session: Session, galaxy: int, system: int, position: int) -> None:
    user = UserRow(
        email=f"filler-{galaxy}-{system}-{position}@example.com",
        username=f"filler{galaxy}{system}{position}",
        password_hash="x",
    )
    session.add(user)
    session.flush()
    session.add(
        PlanetRow(
            user_id=user.id, name="Filler", galaxy=galaxy, system=system, position=position
        )
    )


# --- GET /planets: coordinates -----------------------------------------------


def test_list_planets_returns_coordinates_inside_the_settings(client: TestClient) -> None:
    register_and_login(client, "ada@example.com")

    [planet] = client.get("/planets").json()

    coordinates = planet["coordinates"]
    assert set(coordinates) == {"galaxy", "system", "position"}
    assert 1 <= coordinates["galaxy"] <= get_settings().galaxies
    assert 1 <= coordinates["system"] <= get_settings().systems_per_galaxy
    assert 4 <= coordinates["position"] <= 12


def test_list_planets_gives_the_new_player_the_one_free_position_left(session: Session) -> None:
    app, client = new_client(session)
    set_universe(app, galaxies=1, systems_per_galaxy=1)
    # Fill every home position (4 to 12) but one, leaving only position 12 free.
    for position in range(4, 12):
        fill_position(session, galaxy=1, system=1, position=position)
    session.commit()

    register_and_login(client, "ada@example.com")
    response = client.get("/planets")

    assert response.status_code == 200
    [planet] = response.json()
    assert planet["coordinates"] == {"galaxy": 1, "system": 1, "position": 12}


def test_list_planets_returns_503_when_no_position_is_free(session: Session) -> None:
    app, client = new_client(session)
    set_universe(app, galaxies=1, systems_per_galaxy=1)
    for position in range(4, 13):
        fill_position(session, galaxy=1, system=1, position=position)
    session.commit()

    register_and_login(client, "ada@example.com")
    response = client.get("/planets")

    assert response.status_code == 503


# --- GET /galaxy/{galaxy}/{system} -------------------------------------------


def test_read_galaxy_system_returns_401_without_a_session(client: TestClient) -> None:
    response = client.get("/galaxy/1/1")

    assert response.status_code == 401


def test_read_galaxy_system_returns_404_for_a_galaxy_larger_than_the_universe(
    client: TestClient,
) -> None:
    register_and_login(client, "ada@example.com")

    response = client.get(f"/galaxy/{get_settings().galaxies + 1}/1")

    assert response.status_code == 404


def test_read_galaxy_system_returns_404_for_a_system_larger_than_systems_per_galaxy(
    client: TestClient,
) -> None:
    register_and_login(client, "ada@example.com")

    response = client.get(f"/galaxy/1/{get_settings().systems_per_galaxy + 1}")

    assert response.status_code == 404


@pytest.mark.parametrize(("galaxy", "system"), [(0, 1), (1, 0), (-1, 1)])
def test_read_galaxy_system_returns_422_for_a_value_below_1(
    client: TestClient, galaxy: int, system: int
) -> None:
    register_and_login(client, "ada@example.com")

    response = client.get(f"/galaxy/{galaxy}/{system}")

    assert response.status_code == 422


def test_read_galaxy_system_returns_the_15_positions_in_order_with_the_home_planet(
    client: TestClient,
) -> None:
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()
    coordinates = planet["coordinates"]

    response = client.get(f"/galaxy/{coordinates['galaxy']}/{coordinates['system']}")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"galaxy", "system", "galaxies", "systems_per_galaxy", "positions"}
    assert body["galaxy"] == coordinates["galaxy"]
    assert body["system"] == coordinates["system"]
    assert body["galaxies"] == get_settings().galaxies
    assert body["systems_per_galaxy"] == get_settings().systems_per_galaxy
    assert [position["position"] for position in body["positions"]] == list(range(1, 16))

    own = next(p for p in body["positions"] if p["position"] == coordinates["position"])
    assert own["planet"] == {"name": "Homeworld", "username": "ada"}

    free = next(p for p in body["positions"] if p["position"] != coordinates["position"])
    assert set(free) == {"position"}


def test_read_galaxy_system_shows_another_users_planet_without_the_email(
    client: TestClient,
) -> None:
    register_and_login(client, "ada@example.com")
    [planet] = client.get("/planets").json()
    coordinates = planet["coordinates"]

    register_and_login(client, "bob@example.com")
    response = client.get(f"/galaxy/{coordinates['galaxy']}/{coordinates['system']}")

    assert response.status_code == 200
    position = next(
        p for p in response.json()["positions"] if p["position"] == coordinates["position"]
    )
    assert position["planet"] == {"name": "Homeworld", "username": "ada"}
    assert "ada@example.com" not in response.text
    assert "@example.com" not in response.text
