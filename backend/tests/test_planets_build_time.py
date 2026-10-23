"""Build time: one running upgrade for each planet, completed on read (docs/adr/0114)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.shared.orm.constructions import ConstructionRow
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
NOT_ENOUGH = "Not enough resources for the upgrade"


def start(session: Session, game_speed: float | None = None) -> tuple[FastAPI, TestClient, UUID]:
    """A planet with 1000 metal and 1000 crystal, stored at BASE_TIME. The clock is BASE_TIME."""
    app, client = new_client(session)
    if game_speed is not None:
        set_game_speed(app, game_speed)
    planet_id = home_planet(client)
    set_vault(session, planet_id, metal=1000, crystal=1000, deuterium=0, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME)
    return app, client, planet_id


def building(client: TestClient, planet_id: UUID, kind: str) -> dict:
    [found] = [b for b in client.get(f"/planets/{planet_id}/buildings").json() if b["kind"] == kind]
    return found


def construction_rows(session: Session, planet_id: UUID) -> int:
    count = select(func.count()).select_from(ConstructionRow)
    return session.scalar(count.where(ConstructionRow.planet_id == planet_id)) or 0


# --- The start of an upgrade -----------------------------------------------------


@pytest.mark.parametrize(
    ("game_speed", "seconds"),
    [
        (1, 108),  # 3600 * 75 / 2500
        (10, 10),  # 10.8, rounded down
        (1000, 1),  # 0.108, but at least 1
    ],
)
def test_upgrade_building_build_time(session: Session, game_speed: float, seconds: int) -> None:
    _app, client, planet_id = start(session, game_speed)

    response = client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")

    assert response.status_code == 200
    finishes_at = datetime.fromisoformat(response.json()["building"]["upgrade_finishes_at"])
    assert finishes_at == BASE_TIME + timedelta(seconds=seconds)


def test_upgrade_building_returns_the_old_level_and_the_vault_after_the_cost(
    session: Session,
) -> None:
    _app, client, planet_id = start(session)

    response = client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")

    body = response.json()
    assert body["building"]["kind"] == "metal_mine"
    assert body["building"]["level"] == 0
    assert body["building"]["upgrade_cost"] == {"metal": 60, "crystal": 15, "deuterium": 0}
    assert body["vault"]["metal"] == 1000 - 60
    assert body["vault"]["crystal"] == 1000 - 15
    assert body["vault"]["deuterium"] == 0
    assert body["vault"]["production_per_hour"] == {"metal": 30, "crystal": 15, "deuterium": 0}
    assert body["vault"]["energy"] == {"produced": 0, "used": 0}


def test_upgrade_building_pays_at_the_start_and_raises_the_level_when_it_finishes(
    session: Session,
) -> None:
    app, client, planet_id = start(session)
    client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")

    vault = client.get(f"/planets/{planet_id}/vault").json()
    assert (vault["metal"], vault["crystal"]) == (940, 985)
    assert building(client, planet_id, "metal_mine")["level"] == 0

    set_clock(app, BASE_TIME + timedelta(seconds=107))
    running = building(client, planet_id, "metal_mine")
    assert running["level"] == 0
    assert "upgrade_finishes_at" in running

    set_clock(app, BASE_TIME + timedelta(seconds=108))
    done = building(client, planet_id, "metal_mine")
    assert done["level"] == 1
    assert "upgrade_finishes_at" not in done
    assert construction_rows(session, planet_id) == 0


def test_upgrade_building_returns_409_with_its_own_detail_while_an_upgrade_runs(
    session: Session,
) -> None:
    app, client, planet_id = start(session)
    client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")
    set_clock(app, BASE_TIME + timedelta(seconds=10))
    vault_before = client.get(f"/planets/{planet_id}/vault").json()
    buildings_before = client.get(f"/planets/{planet_id}/buildings").json()

    # A different building, and the same one: both are refused.
    other = client.post(f"/planets/{planet_id}/buildings/solar_plant/upgrade")
    same = client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")

    assert other.status_code == 409
    assert same.status_code == 409
    assert other.json() == same.json()
    assert client.get(f"/planets/{planet_id}/vault").json() == vault_before
    assert client.get(f"/planets/{planet_id}/buildings").json() == buildings_before
    assert construction_rows(session, planet_id) == 1

    # The detail differs from the detail of "not enough resources".
    register_and_login(client, "bob@example.com")
    [bob_planet] = client.get("/planets").json()
    set_vault(session, UUID(bob_planet["id"]), metal=0, crystal=0, deuterium=0)
    poor = client.post(f"/planets/{bob_planet['id']}/buildings/metal_mine/upgrade")
    assert poor.status_code == 409
    assert poor.json()["detail"] == NOT_ENOUGH
    assert same.json()["detail"] != poor.json()["detail"]


def test_upgrade_building_with_a_running_upgrade_and_too_little_reports_the_running_upgrade(
    session: Session,
) -> None:
    _app, client, planet_id = start(session)
    client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")
    set_vault(session, planet_id, metal=0, crystal=0, deuterium=0, updated_at=BASE_TIME)

    response = client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")

    assert response.status_code == 409
    assert response.json()["detail"] != NOT_ENOUGH


def test_upgrade_building_can_start_after_the_running_upgrade_finished(session: Session) -> None:
    app, client, planet_id = start(session)
    client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")
    set_clock(app, BASE_TIME + timedelta(seconds=108))

    response = client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")

    assert response.status_code == 200
    body = response.json()
    # The first upgrade is complete: level 1, and the cost of level 1 to 2 (90 + 22).
    assert body["building"]["level"] == 1
    assert body["building"]["upgrade_cost"] == {"metal": 90, "crystal": 22, "deuterium": 0}
    finishes_at = datetime.fromisoformat(body["building"]["upgrade_finishes_at"])
    # 3600 * (90 + 22) / 2500 = 161.28, started at the finish time of the first upgrade.
    assert finishes_at == BASE_TIME + timedelta(seconds=108 + 161)
    assert body["vault"]["metal"] == 940 - 90
    assert body["vault"]["crystal"] == 985 - 22
    assert construction_rows(session, planet_id) == 1


def test_upgrade_building_with_too_little_after_a_completion_changes_nothing(
    session: Session,
) -> None:
    app, client, planet_id = start(session)
    client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")
    set_vault(session, planet_id, metal=0, crystal=0, deuterium=0, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME + timedelta(seconds=108))

    response = client.post(f"/planets/{planet_id}/buildings/crystal_mine/upgrade")

    assert response.status_code == 409
    assert response.json()["detail"] == NOT_ENOUGH
    # A later read completes the upgrade and gives the same result as without the failed start.
    assert building(client, planet_id, "metal_mine")["level"] == 1
    assert construction_rows(session, planet_id) == 0


def test_upgrade_building_by_another_user_while_one_runs_returns_404_and_changes_nothing(
    session: Session,
) -> None:
    app, client, planet_id = start(session)
    client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")
    set_clock(app, BASE_TIME + timedelta(seconds=10))
    vault_before = client.get(f"/planets/{planet_id}/vault").json()
    buildings_before = client.get(f"/planets/{planet_id}/buildings").json()
    unknown = client.post(f"/planets/{UNKNOWN_PLANET}/buildings/solar_plant/upgrade")

    register_and_login(client, "bob@example.com")
    other_users = client.post(f"/planets/{planet_id}/buildings/solar_plant/upgrade")

    assert other_users.status_code == 404
    assert other_users.json() == unknown.json()
    register_and_login(client, "ada@example.com")
    assert client.get(f"/planets/{planet_id}/vault").json() == vault_before
    assert client.get(f"/planets/{planet_id}/buildings").json() == buildings_before
    assert construction_rows(session, planet_id) == 1


def test_upgrade_building_by_another_user_after_the_finish_time_does_not_complete_it(
    session: Session,
) -> None:
    app, client, planet_id = start(session)
    client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")
    set_clock(app, BASE_TIME + timedelta(hours=1))

    register_and_login(client, "bob@example.com")
    assert client.post(f"/planets/{planet_id}/buildings/solar_plant/upgrade").status_code == 404
    assert client.get(f"/planets/{planet_id}/vault").status_code == 404
    assert client.get(f"/planets/{planet_id}/buildings").status_code == 404

    assert construction_rows(session, planet_id) == 1


# --- Completion on read ----------------------------------------------------------


def test_read_vault_counts_the_old_level_before_the_finish_time_and_the_new_one_after(
    session: Session,
) -> None:
    app, client, planet_id = start(session)
    # Solar plant 5 makes 161 energy, so the factor is 1 at level 0 and level 1.
    set_building_level(session, planet_id, "solar_plant", 5)
    client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")

    set_clock(app, BASE_TIME + timedelta(hours=1))
    vault = client.get(f"/planets/{planet_id}/vault").json()

    # Level 0 for 108 s: 30/h gives 0.9, stored as 0. Level 1 for 3492 s: 63/h gives 61.11.
    # (Level 0 all hour: 970. Level 1 all hour: 1003.)
    assert vault["production_per_hour"]["metal"] == 63
    assert vault["metal"] == 940 + 61
    assert vault["crystal"] == 985 + 14
    row = session.scalars(select(VaultRow).where(VaultRow.planet_id == planet_id)).one()
    session.refresh(row)
    assert row.updated_at == BASE_TIME + timedelta(seconds=108)


def test_read_vault_stores_the_amounts_at_the_finish_time_with_the_old_levels(
    session: Session,
) -> None:
    app, client, planet_id = start(session, game_speed=10)
    set_building_level(session, planet_id, "solar_plant", 5)
    client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")
    set_clock(app, BASE_TIME + timedelta(hours=1))

    vault = client.get(f"/planets/{planet_id}/vault").json()

    # Build time 10 s. Level 0 makes 300/h, level 1 makes 300 + 330 = 630/h.
    assert vault["production_per_hour"]["metal"] == 630
    # 940 + floor(300 * 10/3600) = 940, then 940 + floor(630 * 3590/3600) = 940 + 628.
    assert vault["metal"] == 940 + 628


def test_read_vault_completes_a_due_upgrade_once(session: Session) -> None:
    app, client, planet_id = start(session)
    client.post(f"/planets/{planet_id}/buildings/metal_mine/upgrade")
    set_clock(app, BASE_TIME + timedelta(hours=1))

    first = client.get(f"/planets/{planet_id}/vault")
    second = client.get(f"/planets/{planet_id}/vault")

    assert first.json() == second.json()
    assert building(client, planet_id, "metal_mine")["level"] == 1
    assert construction_rows(session, planet_id) == 0


def test_list_buildings_shows_upgrade_finishes_at_only_on_the_running_building(
    session: Session,
) -> None:
    _app, client, planet_id = start(session)
    client.post(f"/planets/{planet_id}/buildings/crystal_mine/upgrade")

    body = client.get(f"/planets/{planet_id}/buildings").json()

    with_field = [b["kind"] for b in body if "upgrade_finishes_at" in b]
    assert with_field == ["crystal_mine"]
    assert all(b.get("upgrade_finishes_at") is not None for b in body if "upgrade_finishes_at" in b)
    # 3600 * (48 + 24) / 2500 = 103.68
    crystal_mine = body[1]
    assert datetime.fromisoformat(crystal_mine["upgrade_finishes_at"]) == BASE_TIME + timedelta(
        seconds=103
    )


def test_list_buildings_has_no_upgrade_finishes_at_without_a_running_upgrade(
    session: Session,
) -> None:
    _app, client, planet_id = start(session)

    body = client.get(f"/planets/{planet_id}/buildings").json()

    assert all("upgrade_finishes_at" not in b for b in body)


def test_read_does_not_go_back_in_time_for_a_finish_time_before_the_stored_time(
    session: Session,
) -> None:
    app, client, planet_id = start(session)
    finishes_at = BASE_TIME - timedelta(hours=1)
    session.add(ConstructionRow(planet_id=planet_id, kind="metal_mine", finishes_at=finishes_at))
    session.commit()
    set_clock(app, BASE_TIME + timedelta(hours=1))

    vault = client.get(f"/planets/{planet_id}/vault").json()

    # The stored time is BASE_TIME. The amounts are stored at BASE_TIME, not an hour before.
    # Level 1 with no solar plant: factor 0, so only the base income of 1 hour.
    assert vault["metal"] == 1000 + 30
    assert building(client, planet_id, "metal_mine")["level"] == 1
    row = session.scalars(select(VaultRow).where(VaultRow.planet_id == planet_id)).one()
    session.refresh(row)
    assert row.updated_at == BASE_TIME
