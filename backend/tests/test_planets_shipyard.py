"""Shipyard: ships, one order at a time, completed on read (docs/adr/0115)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.shared.orm.constructions import ConstructionRow
from app.shared.orm.ships import ShipOrderRow, ShipRow
from app.shared.orm.vaults import VaultRow
from tests.test_planets import (
    new_client,
    register_and_login,
    set_building_level,
    set_clock,
    set_game_speed,
)
from tests.test_planets_storage import home_planet, set_vault

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
UNKNOWN_PLANET = "00000000-0000-0000-0000-000000000000"
SMALL_CARGO_SECONDS = 2880  # 3600 * 4000 / 2500 / (1 + 1)
NO_SHIPYARD = "The shipyard has level 0"
ORDER_RUNNING = "A ship order is already running on the planet"
NOT_ENOUGH = "Not enough resources for the ships"


def start(
    session: Session, shipyard_level: int = 1, game_speed: float | None = None
) -> tuple[FastAPI, TestClient, UUID]:
    """A planet with a full vault (10000 metal and crystal, 1000 deuterium) stored at BASE_TIME."""
    app, client = new_client(session)
    if game_speed is not None:
        set_game_speed(app, game_speed)
    planet_id = home_planet(client)
    set_vault(
        session, planet_id, metal=10000, crystal=10000, deuterium=1000, updated_at=BASE_TIME
    )
    if shipyard_level:
        set_building_level(session, planet_id, "shipyard", shipyard_level)
    set_clock(app, BASE_TIME)
    return app, client, planet_id


def order(client: TestClient, planet_id: UUID | str, kind: str, count: int) -> Response:
    return client.post(f"/planets/{planet_id}/ships/{kind}/order", json={"count": count})


def shipyard(client: TestClient, planet_id: UUID) -> dict:
    response = client.get(f"/planets/{planet_id}/ships")
    assert response.status_code == 200
    return response.json()


def ship(body: dict, kind: str) -> dict:
    [found] = [s for s in body["ships"] if s["kind"] == kind]
    return found


def count_of(session: Session, planet_id: UUID, kind: str) -> int:
    session.expire_all()
    row = session.get(ShipRow, (planet_id, kind))
    return row.count if row else 0


def order_rows(session: Session, planet_id: UUID) -> int:
    session.expire_all()
    rows = select(func.count()).select_from(ShipOrderRow)
    return session.scalar(rows.where(ShipOrderRow.planet_id == planet_id)) or 0


def iso(when: datetime) -> str:
    return when.isoformat().replace("+00:00", "Z")


def has_null(node: object) -> bool:
    if node is None:
        return True
    if isinstance(node, dict):
        return any(has_null(value) for value in node.values())
    if isinstance(node, list):
        return any(has_null(value) for value in node)
    return False


# --- The shipyard as a building ---------------------------------------------------


def test_list_buildings_has_the_shipyard_last_with_its_cost_at_each_level(
    session: Session,
) -> None:
    _app, client, planet_id = start(session, shipyard_level=0)

    level_0 = client.get(f"/planets/{planet_id}/buildings").json()[-1]
    assert level_0["kind"] == "shipyard"
    assert level_0["level"] == 0
    assert level_0["production_per_hour"] == 0
    assert level_0["energy"] == {"produced": 0, "used": 0}
    assert level_0["upgrade_cost"] == {"metal": 400, "crystal": 200, "deuterium": 100}

    set_building_level(session, planet_id, "shipyard", 3)
    level_3 = client.get(f"/planets/{planet_id}/buildings").json()[-1]
    assert level_3["upgrade_cost"] == {"metal": 3200, "crystal": 1600, "deuterium": 800}


def test_shipyard_upgrade_follows_the_build_time_rules(session: Session) -> None:
    app, client, planet_id = start(session, shipyard_level=0)

    response = client.post(f"/planets/{planet_id}/buildings/shipyard/upgrade")

    assert response.status_code == 200
    body = response.json()
    assert body["building"]["kind"] == "shipyard"
    assert body["building"]["level"] == 0
    assert body["vault"]["metal"] == 10000 - 400
    assert body["vault"]["crystal"] == 10000 - 200
    assert body["vault"]["deuterium"] == 1000 - 100
    # 3600 * (400 + 200) / 2500
    finishes_at = datetime.fromisoformat(body["building"]["upgrade_finishes_at"])
    assert finishes_at == BASE_TIME + timedelta(seconds=864)

    set_clock(app, BASE_TIME + timedelta(seconds=864))
    buildings = client.get(f"/planets/{planet_id}/buildings").json()
    assert buildings[-1]["kind"] == "shipyard"
    assert buildings[-1]["level"] == 1
    assert "upgrade_finishes_at" not in buildings[-1]


# --- GET /planets/{planet_id}/ships -----------------------------------------------


def test_read_shipyard_returns_401_without_a_session(client: TestClient) -> None:
    response = client.get(f"/planets/{UNKNOWN_PLANET}/ships")

    assert response.status_code == 401


def test_read_shipyard_returns_422_for_a_planet_id_that_is_not_a_uuid(client: TestClient) -> None:
    home_planet(client)

    response = client.get("/planets/not-a-uuid/ships")

    assert response.status_code == 422


def test_read_shipyard_returns_the_two_ships_with_cost_and_build_time(session: Session) -> None:
    _app, client, planet_id = start(session, shipyard_level=1)

    body = shipyard(client, planet_id)

    assert [s["kind"] for s in body["ships"]] == ["small_cargo", "light_fighter"]
    assert body["ships"][0] == {
        "kind": "small_cargo",
        "count": 0,
        "cost": {"metal": 2000, "crystal": 2000, "deuterium": 0},
        "build_seconds": 2880,
    }
    assert body["ships"][1] == {
        "kind": "light_fighter",
        "count": 0,
        "cost": {"metal": 3000, "crystal": 1000, "deuterium": 0},
        "build_seconds": 2880,
    }


def test_read_shipyard_has_no_order_key_and_no_null_without_an_order(session: Session) -> None:
    _app, client, planet_id = start(session)

    body = shipyard(client, planet_id)

    assert "order" not in body
    assert not has_null(body)


@pytest.mark.parametrize(
    ("shipyard_level", "game_speed", "seconds"),
    [
        (0, 1, 5760),  # 3600 * 4000 / 2500 / 1
        (1, 1, 2880),
        (3, 1, 1440),  # 5760 / 4
        (1, 10, 288),
        (1, 7, 411),  # 411.4, rounded down
        (1, 1_000_000, 1),  # 0.00288, but at least 1
    ],
)
def test_read_shipyard_build_seconds(
    session: Session, shipyard_level: int, game_speed: float, seconds: int
) -> None:
    _app, client, planet_id = start(session, shipyard_level, game_speed)

    body = shipyard(client, planet_id)

    assert [s["build_seconds"] for s in body["ships"]] == [seconds, seconds]


def test_read_shipyard_returns_404_for_another_users_planet_like_for_an_unknown_one(
    session: Session,
) -> None:
    _app, client, planet_id = start(session)
    unknown = client.get(f"/planets/{UNKNOWN_PLANET}/ships")

    register_and_login(client, "bob@example.com")
    other_users = client.get(f"/planets/{planet_id}/ships")

    assert other_users.status_code == 404
    assert other_users.json() == unknown.json()


# --- POST /planets/{planet_id}/ships/{kind}/order ---------------------------------


def test_order_ships_returns_401_without_a_session(client: TestClient) -> None:
    response = order(client, UNKNOWN_PLANET, "small_cargo", 1)

    assert response.status_code == 401


def test_order_ships_pays_at_the_start_and_returns_the_order_and_the_vault(
    session: Session,
) -> None:
    _app, client, planet_id = start(session)

    response = order(client, planet_id, "small_cargo", 3)

    assert response.status_code == 200
    body = response.json()
    assert body["vault"]["metal"] == 10000 - 3 * 2000
    assert body["vault"]["crystal"] == 10000 - 3 * 2000
    assert body["vault"]["deuterium"] == 1000
    assert body["shipyard"]["order"] == {
        "kind": "small_cargo",
        "remaining": 3,
        "next_finishes_at": iso(BASE_TIME + timedelta(seconds=2880)),
        "finishes_at": iso(BASE_TIME + timedelta(seconds=3 * 2880)),
    }
    assert [s["count"] for s in body["shipyard"]["ships"]] == [0, 0]
    assert not has_null(body)
    assert client.get(f"/planets/{planet_id}/vault").json()["metal"] == 4000


def test_order_ships_light_fighter_costs_3000_metal_and_1000_crystal_each(
    session: Session,
) -> None:
    _app, client, planet_id = start(session)

    response = order(client, planet_id, "light_fighter", 2)

    body = response.json()
    assert (body["vault"]["metal"], body["vault"]["crystal"]) == (10000 - 6000, 10000 - 2000)
    assert body["shipyard"]["order"]["kind"] == "light_fighter"


def test_order_ships_adds_the_production_up_to_now_before_it_subtracts_the_cost(
    session: Session,
) -> None:
    app, client, planet_id = start(session)
    set_vault(session, planet_id, metal=2000, crystal=2000, deuterium=0, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME + timedelta(hours=2))

    response = order(client, planet_id, "small_cargo", 1)

    # Base income 30 metal and 15 crystal per hour.
    assert response.status_code == 200
    assert response.json()["vault"]["metal"] == 2000 + 60 - 2000
    assert response.json()["vault"]["crystal"] == 2000 + 30 - 2000


@pytest.mark.parametrize("count", [0, -1, 1001])
def test_order_ships_returns_422_for_a_count_outside_1_to_1000(
    session: Session, count: int
) -> None:
    _app, client, planet_id = start(session)

    response = order(client, planet_id, "small_cargo", count)

    assert response.status_code == 422
    assert order_rows(session, planet_id) == 0


def test_order_ships_returns_422_for_a_missing_count_and_for_an_unknown_kind(
    session: Session,
) -> None:
    _app, client, planet_id = start(session)

    missing = client.post(f"/planets/{planet_id}/ships/small_cargo/order", json={})
    unknown = order(client, planet_id, "battleship", 1)

    assert missing.status_code == 422
    assert unknown.status_code == 422
    assert order_rows(session, planet_id) == 0


def test_order_ships_accepts_a_count_of_1000(session: Session) -> None:
    _app, client, planet_id = start(session)
    set_vault(session, planet_id, metal=0, crystal=0, deuterium=0, updated_at=BASE_TIME)

    too_little = order(client, planet_id, "small_cargo", 1000)

    # 1000 passes the validation. The vault is too small, so it is a 409, not a 422.
    assert too_little.status_code == 409


def test_order_ships_by_another_user_returns_404_and_changes_nothing(session: Session) -> None:
    _app, client, planet_id = start(session)
    unknown = order(client, UNKNOWN_PLANET, "small_cargo", 1)
    vault_before = client.get(f"/planets/{planet_id}/vault").json()
    ships_before = shipyard(client, planet_id)

    register_and_login(client, "bob@example.com")
    other_users = order(client, planet_id, "small_cargo", 1)

    assert other_users.status_code == 404
    assert other_users.json() == unknown.json()

    register_and_login(client, "ada@example.com")
    assert client.get(f"/planets/{planet_id}/vault").json() == vault_before
    assert shipyard(client, planet_id) == ships_before
    assert order_rows(session, planet_id) == 0


# --- The three 409 reasons ----------------------------------------------------------


def test_order_ships_409_reasons_have_three_different_details_and_change_nothing(
    session: Session,
) -> None:
    app, client, planet_id = start(session, shipyard_level=0)

    # 1. The shipyard has level 0.
    no_shipyard = order(client, planet_id, "small_cargo", 1)

    # 2. An order runs.
    set_building_level(session, planet_id, "shipyard", 1)
    assert order(client, planet_id, "small_cargo", 1).status_code == 200
    set_clock(app, BASE_TIME + timedelta(seconds=10))
    vault_before = client.get(f"/planets/{planet_id}/vault").json()
    ships_before = shipyard(client, planet_id)
    running = order(client, planet_id, "light_fighter", 1)
    assert client.get(f"/planets/{planet_id}/vault").json() == vault_before
    assert shipyard(client, planet_id) == ships_before

    # 3. The vault has too little.
    register_and_login(client, "bob@example.com")
    [bob_planet] = client.get("/planets").json()
    bob_id = UUID(bob_planet["id"])
    set_building_level(session, bob_id, "shipyard", 1)
    set_vault(session, bob_id, metal=1999, crystal=2000, deuterium=0)
    poor = order(client, bob_id, "small_cargo", 1)
    bob_vault = client.get(f"/planets/{bob_id}/vault").json()

    assert (no_shipyard.status_code, running.status_code, poor.status_code) == (409, 409, 409)
    assert no_shipyard.json()["detail"] == NO_SHIPYARD
    assert running.json()["detail"] == ORDER_RUNNING
    assert poor.json()["detail"] == NOT_ENOUGH
    assert bob_vault["metal"] == 1999
    assert order_rows(session, bob_id) == 0
    assert order_rows(session, planet_id) == 1


def test_order_ships_with_shipyard_level_0_changes_nothing(session: Session) -> None:
    _app, client, planet_id = start(session, shipyard_level=0)
    vault_before = client.get(f"/planets/{planet_id}/vault").json()

    response = order(client, planet_id, "small_cargo", 1)

    assert response.status_code == 409
    assert client.get(f"/planets/{planet_id}/vault").json() == vault_before
    assert order_rows(session, planet_id) == 0


def test_order_ships_reports_the_missing_shipyard_before_the_missing_resources(
    session: Session,
) -> None:
    _app, client, planet_id = start(session, shipyard_level=0)
    set_vault(session, planet_id, metal=0, crystal=0, deuterium=0, updated_at=BASE_TIME)

    response = order(client, planet_id, "small_cargo", 1)

    assert response.json()["detail"] == NO_SHIPYARD


def test_order_ships_reports_the_running_order_before_the_missing_resources(
    session: Session,
) -> None:
    app, client, planet_id = start(session)
    assert order(client, planet_id, "small_cargo", 3).status_code == 200
    set_vault(session, planet_id, metal=0, crystal=0, deuterium=0, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME + timedelta(seconds=10))

    response = order(client, planet_id, "small_cargo", 1)

    assert response.status_code == 409
    assert response.json()["detail"] == ORDER_RUNNING


def test_order_ships_too_little_of_one_resource_is_enough_to_refuse(session: Session) -> None:
    _app, client, planet_id = start(session)
    set_vault(session, planet_id, metal=6000, crystal=5999, deuterium=0, updated_at=BASE_TIME)

    response = order(client, planet_id, "small_cargo", 3)

    assert response.status_code == 409
    assert order_rows(session, planet_id) == 0
    vault = client.get(f"/planets/{planet_id}/vault").json()
    assert (vault["metal"], vault["crystal"]) == (6000, 5999)


# --- Completion on read -------------------------------------------------------------


def test_an_order_of_3_completes_one_ship_at_a_time(session: Session) -> None:
    app, client, planet_id = start(session)
    assert order(client, planet_id, "small_cargo", 3).status_code == 200

    set_clock(app, BASE_TIME + timedelta(seconds=SMALL_CARGO_SECONDS - 1))
    before = shipyard(client, planet_id)
    assert ship(before, "small_cargo")["count"] == 0
    assert before["order"]["remaining"] == 3

    set_clock(app, BASE_TIME + timedelta(seconds=SMALL_CARGO_SECONDS))
    first = shipyard(client, planet_id)
    assert ship(first, "small_cargo")["count"] == 1
    assert first["order"]["remaining"] == 2
    assert datetime.fromisoformat(first["order"]["next_finishes_at"]) == BASE_TIME + timedelta(
        seconds=2 * SMALL_CARGO_SECONDS
    )
    assert datetime.fromisoformat(first["order"]["finishes_at"]) == BASE_TIME + timedelta(
        seconds=3 * SMALL_CARGO_SECONDS
    )

    set_clock(app, BASE_TIME + timedelta(seconds=3 * SMALL_CARGO_SECONDS))
    done = shipyard(client, planet_id)
    assert ship(done, "small_cargo")["count"] == 3
    assert "order" not in done
    assert order_rows(session, planet_id) == 0
    assert count_of(session, planet_id, "small_cargo") == 3


def test_a_read_long_after_the_order_completes_all_the_ships_at_once(session: Session) -> None:
    app, client, planet_id = start(session)
    order(client, planet_id, "light_fighter", 2)

    set_clock(app, BASE_TIME + timedelta(days=30))
    body = shipyard(client, planet_id)

    assert ship(body, "light_fighter")["count"] == 2
    assert ship(body, "small_cargo")["count"] == 0
    assert "order" not in body


def test_a_read_after_two_of_three_ships_are_due_adds_exactly_two(session: Session) -> None:
    app, client, planet_id = start(session)
    order(client, planet_id, "small_cargo", 3)

    set_clock(app, BASE_TIME + timedelta(seconds=2 * SMALL_CARGO_SECONDS + 5))
    body = shipyard(client, planet_id)

    assert ship(body, "small_cargo")["count"] == 2
    assert body["order"]["remaining"] == 1
    assert datetime.fromisoformat(body["order"]["next_finishes_at"]) == BASE_TIME + timedelta(
        seconds=3 * SMALL_CARGO_SECONDS
    )
    # A second read at the same time adds nothing.
    assert shipyard(client, planet_id) == body
    assert count_of(session, planet_id, "small_cargo") == 2


def test_ships_add_to_the_count_that_was_there_before(session: Session) -> None:
    app, client, planet_id = start(session)
    session.add(ShipRow(planet_id=planet_id, kind="small_cargo", count=5))
    session.commit()
    order(client, planet_id, "small_cargo", 1)

    set_clock(app, BASE_TIME + timedelta(seconds=SMALL_CARGO_SECONDS))

    assert ship(shipyard(client, planet_id), "small_cargo")["count"] == 6


def test_ships_do_not_change_the_vault_when_they_complete(session: Session) -> None:
    app, client, planet_id = start(session)
    order(client, planet_id, "small_cargo", 1)
    set_clock(app, BASE_TIME + timedelta(seconds=SMALL_CARGO_SECONDS))
    # Reading the vault does not complete ships, so this read is before the completion.
    before = client.get(f"/planets/{planet_id}/vault").json()

    assert ship(shipyard(client, planet_id), "small_cargo")["count"] == 1

    assert client.get(f"/planets/{planet_id}/vault").json() == before


def test_an_order_start_completes_the_due_ships_first_and_then_starts_the_new_order(
    session: Session,
) -> None:
    app, client, planet_id = start(session)
    order(client, planet_id, "small_cargo", 1)

    set_clock(app, BASE_TIME + timedelta(seconds=SMALL_CARGO_SECONDS))
    response = order(client, planet_id, "light_fighter", 1)

    assert response.status_code == 200
    body = response.json()
    assert ship(body["shipyard"], "small_cargo")["count"] == 1
    assert body["shipyard"]["order"]["kind"] == "light_fighter"
    assert count_of(session, planet_id, "small_cargo") == 1


def test_a_new_order_can_start_after_the_last_ship_is_complete(session: Session) -> None:
    app, client, planet_id = start(session)
    order(client, planet_id, "small_cargo", 1)
    set_clock(app, BASE_TIME + timedelta(seconds=SMALL_CARGO_SECONDS - 1))
    assert order(client, planet_id, "small_cargo", 1).status_code == 409

    set_clock(app, BASE_TIME + timedelta(seconds=SMALL_CARGO_SECONDS))
    assert order(client, planet_id, "small_cargo", 1).status_code == 200


def test_order_ships_with_the_clock_before_the_stored_time_never_stores_an_earlier_time(
    session: Session,
) -> None:
    app, client, planet_id = start(session)
    set_clock(app, BASE_TIME - timedelta(hours=1))

    response = order(client, planet_id, "small_cargo", 1)

    assert response.status_code == 200
    session.expire_all()
    vault = session.get(VaultRow, planet_id)
    assert vault is not None
    assert vault.updated_at >= BASE_TIME


# --- The order and the building upgrade ---------------------------------------------


def test_a_shipyard_upgrade_during_an_order_does_not_change_the_order_time(
    session: Session,
) -> None:
    app, client, planet_id = start(session, shipyard_level=1)
    assert order(client, planet_id, "small_cargo", 3).status_code == 200

    # The upgrade from level 1 to 2 takes 3600 * 1200 / 2500 = 1728 seconds.
    assert client.post(f"/planets/{planet_id}/buildings/shipyard/upgrade").status_code == 200
    set_clock(app, BASE_TIME + timedelta(seconds=1728))
    during = shipyard(client, planet_id)

    # The shipyard is level 2 now. The new ships are faster, but the order keeps its time.
    assert [s["build_seconds"] for s in during["ships"]] == [1920, 1920]
    assert during["order"]["remaining"] == 3
    assert datetime.fromisoformat(during["order"]["next_finishes_at"]) == BASE_TIME + timedelta(
        seconds=SMALL_CARGO_SECONDS
    )

    set_clock(app, BASE_TIME + timedelta(seconds=SMALL_CARGO_SECONDS))
    first = shipyard(client, planet_id)
    assert ship(first, "small_cargo")["count"] == 1
    assert datetime.fromisoformat(first["order"]["next_finishes_at"]) == BASE_TIME + timedelta(
        seconds=2 * SMALL_CARGO_SECONDS
    )
    assert datetime.fromisoformat(first["order"]["finishes_at"]) == BASE_TIME + timedelta(
        seconds=3 * SMALL_CARGO_SECONDS
    )


def test_an_order_and_a_building_upgrade_run_at_the_same_time(session: Session) -> None:
    app, client, planet_id = start(session)

    upgrade = client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")
    ordered = order(client, planet_id, "small_cargo", 1)

    assert upgrade.status_code == 200
    assert ordered.status_code == 200
    assert order_rows(session, planet_id) == 1
    constructions = select(func.count()).select_from(ConstructionRow)
    assert session.scalar(constructions.where(ConstructionRow.planet_id == planet_id)) == 1

    # The upgrade of the metal mine does not block a ship order, and the reverse.
    set_clock(app, BASE_TIME + timedelta(seconds=108))
    buildings = client.get(f"/planets/{planet_id}/buildings").json()
    assert buildings[0]["kind"] == "metal_mine"
    assert buildings[0]["level"] == 1
    assert shipyard(client, planet_id)["order"]["remaining"] == 1
