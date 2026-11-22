"""The research lab, the two technologies, and their effects (docs/adr/0117)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.shared.orm.constructions import ConstructionRow
from app.shared.orm.research import ResearchRow, TechnologyRow
from app.shared.orm.users import UserRow
from app.shared.orm.vaults import VaultRow
from tests.test_planets import (
    NOT_FOUND,
    new_client,
    register_and_login,
    set_building_level,
    set_clock,
)

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)

NO_LAB = "The research lab of the planet has level 0"
RESEARCH_RUNNING = "A research is already running"
TECH_NOT_AVAILABLE = "A required technology level is missing"
NOT_ENOUGH = "Not enough resources for the research"


def home_planet(client: TestClient, email: str = "ada@example.com") -> UUID:
    register_and_login(client, email)
    [planet] = client.get("/planets").json()
    return UUID(planet["id"])


def user_id_of(session: Session, email: str) -> UUID:
    return session.scalars(select(UserRow.id).where(UserRow.email == email)).one()


def set_technology_level(session: Session, user_id: UUID, kind: str, level: int) -> None:
    session.add(TechnologyRow(user_id=user_id, kind=kind, level=level))
    session.commit()


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


# --- GET /planets/{planet_id}/buildings: the research lab -------------------------------


def test_list_buildings_has_the_research_lab_last_with_its_cost_at_each_level(
    session: Session,
) -> None:
    _app, client = new_client(session)
    planet_id = home_planet(client)

    level_0 = client.get(f"/planets/{planet_id}/buildings").json()[-1]
    assert level_0["kind"] == "research_lab"
    assert level_0["level"] == 0
    assert level_0["production_per_hour"] == 0
    assert level_0["energy"] == {"produced": 0, "used": 0}
    assert level_0["upgrade_cost"] == {"metal": 200, "crystal": 400, "deuterium": 200}

    set_building_level(session, planet_id, "research_lab", 2)
    level_2 = client.get(f"/planets/{planet_id}/buildings").json()[-1]
    assert level_2["upgrade_cost"] == {"metal": 800, "crystal": 1600, "deuterium": 800}


# --- The effects of energy technology and plasma technology (docs/adr/0117) --------------


def test_solar_plant_level_1_gives_22_energy_at_energy_technology_0_and_24_at_1(
    session: Session,
) -> None:
    _app, client = new_client(session)
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "solar_plant", 1)

    before = client.get(f"/planets/{planet_id}/buildings").json()[3]
    assert before["kind"] == "solar_plant"
    assert before["energy"]["produced"] == 22

    user_id = user_id_of(session, "ada@example.com")
    set_technology_level(session, user_id, "energy_technology", 1)

    after = client.get(f"/planets/{planet_id}/buildings").json()[3]
    assert after["energy"]["produced"] == 24


def test_metal_mine_level_1_with_plasma_technology_1_produces_33_at_factor_1(
    session: Session,
) -> None:
    _app, client = new_client(session)
    planet_id = home_planet(client)
    # Solar plant 5 makes 161 energy, metal mine 1 uses 11: factor 1.
    set_building_level(session, planet_id, "solar_plant", 5)
    set_building_level(session, planet_id, "metal_mine", 1)
    user_id = user_id_of(session, "ada@example.com")
    set_technology_level(session, user_id, "plasma_technology", 1)

    metal_mine = client.get(f"/planets/{planet_id}/buildings").json()[0]

    # floor(30 * 1.1 * 1.01) = floor(33.33) = 33.
    assert metal_mine["production_per_hour"] == 33


def test_the_plasma_bonus_does_not_apply_to_the_base_income(session: Session) -> None:
    _app, client = new_client(session)
    planet_id = home_planet(client)
    user_id = user_id_of(session, "ada@example.com")
    set_technology_level(session, user_id, "plasma_technology", 100)

    vault = client.get(f"/planets/{planet_id}/vault").json()

    assert vault["production_per_hour"] == {"metal": 30, "crystal": 15, "deuterium": 0}


# --- GET /research ------------------------------------------------------------------------


def test_read_research_returns_401_without_a_session(client: TestClient) -> None:
    response = client.get("/research")

    assert response.status_code == 401


def test_read_research_returns_both_technologies_in_order_at_level_0(client: TestClient) -> None:
    register_and_login(client, "ada@example.com")

    response = client.get("/research")

    assert response.status_code == 200
    body = response.json()
    assert "running" not in body
    assert [tech["kind"] for tech in body["technologies"]] == [
        "energy_technology",
        "plasma_technology",
    ]
    energy, plasma = body["technologies"]
    assert energy["level"] == 0
    assert energy["cost"] == {"metal": 0, "crystal": 800, "deuterium": 400}
    assert energy["available"] is True
    assert plasma["level"] == 0
    assert plasma["cost"] == {"metal": 2000, "crystal": 4000, "deuterium": 1000}
    assert plasma["available"] is False


def test_read_research_plasma_is_available_after_energy_technology_level_1(
    client: TestClient, session: Session
) -> None:
    register_and_login(client, "ada@example.com")
    user_id = user_id_of(session, "ada@example.com")
    set_technology_level(session, user_id, "energy_technology", 1)

    body = client.get("/research").json()

    assert body["technologies"][1]["available"] is True
    assert body["technologies"][1]["cost"] == {"metal": 2000, "crystal": 4000, "deuterium": 1000}


def test_read_research_cost_grows_with_the_level(client: TestClient, session: Session) -> None:
    register_and_login(client, "ada@example.com")
    user_id = user_id_of(session, "ada@example.com")
    set_technology_level(session, user_id, "energy_technology", 2)

    body = client.get("/research").json()

    assert body["technologies"][0]["level"] == 2
    assert body["technologies"][0]["cost"] == {"metal": 0, "crystal": 3200, "deuterium": 1600}


# --- POST /planets/{planet_id}/research/{kind}/start --------------------------------------


def test_start_research_returns_401_without_a_session(client: TestClient) -> None:
    response = client.post(
        "/planets/00000000-0000-0000-0000-000000000000/research/energy_technology/start"
    )

    assert response.status_code == 401


def test_start_research_returns_404_for_an_unknown_planet(client: TestClient) -> None:
    register_and_login(client, "ada@example.com")

    response = client.post(
        "/planets/00000000-0000-0000-0000-000000000000/research/energy_technology/start"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND


def test_start_research_returns_422_for_an_unknown_kind(client: TestClient) -> None:
    planet_id = home_planet(client)

    response = client.post(f"/planets/{planet_id}/research/hyperspace_technology/start")

    assert response.status_code == 422


def test_start_research_by_another_user_returns_404_and_changes_nothing(session: Session) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client, "ada@example.com")
    set_building_level(session, planet_id, "research_lab", 1)
    set_vault(session, planet_id, metal=10000, crystal=10000, deuterium=10000, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME)
    vault_before = client.get(f"/planets/{planet_id}/vault").json()
    research_before = client.get("/research").json()

    register_and_login(client, "bob@example.com")
    response = client.post(f"/planets/{planet_id}/research/energy_technology/start")

    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND
    assert "running" not in client.get("/research").json()

    register_and_login(client, "ada@example.com")
    assert client.get(f"/planets/{planet_id}/vault").json() == vault_before
    assert client.get("/research").json() == research_before


def test_start_research_energy_technology_takes_1440_seconds_at_lab_level_1(
    session: Session,
) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "research_lab", 1)
    set_vault(session, planet_id, metal=100, crystal=1000, deuterium=1000, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME)

    response = client.post(f"/planets/{planet_id}/research/energy_technology/start")

    assert response.status_code == 200
    body = response.json()
    running = body["research"]["running"]
    assert running["kind"] == "energy_technology"
    assert running["planet_id"] == str(planet_id)
    # 3600 * (0 + 800) / 1000 / (1 + 1) = 1440 seconds.
    finishes_at = datetime.fromisoformat(running["finishes_at"])
    assert finishes_at == BASE_TIME + timedelta(seconds=1440)
    assert body["vault"]["metal"] == 100
    assert body["vault"]["crystal"] == 1000 - 800
    assert body["vault"]["deuterium"] == 1000 - 400
    assert body["research"]["technologies"][0]["level"] == 0


def test_plasma_technology_without_energy_technology_returns_409_and_is_unavailable(
    session: Session,
) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "research_lab", 1)
    set_vault(
        session, planet_id, metal=100000, crystal=100000, deuterium=100000, updated_at=BASE_TIME
    )
    set_clock(app, BASE_TIME)

    response = client.post(f"/planets/{planet_id}/research/plasma_technology/start")

    assert response.status_code == 409
    research = client.get("/research").json()
    assert research["technologies"][1]["kind"] == "plasma_technology"
    assert research["technologies"][1]["available"] is False


def test_start_research_reports_the_missing_lab_before_other_reasons(session: Session) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_vault(session, planet_id, metal=0, crystal=0, deuterium=0, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME)

    response = client.post(f"/planets/{planet_id}/research/plasma_technology/start")

    assert response.status_code == 409
    assert response.json()["detail"] == NO_LAB


def test_start_research_reports_the_running_research_before_the_missing_technology(
    session: Session,
) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "research_lab", 1)
    set_vault(
        session, planet_id, metal=100000, crystal=100000, deuterium=100000, updated_at=BASE_TIME
    )
    set_clock(app, BASE_TIME)
    start = client.post(f"/planets/{planet_id}/research/energy_technology/start")
    assert start.status_code == 200

    response = client.post(f"/planets/{planet_id}/research/plasma_technology/start")

    assert response.status_code == 409
    assert response.json()["detail"] == RESEARCH_RUNNING


def test_start_research_reports_the_missing_technology_before_insufficient_resources(
    session: Session,
) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "research_lab", 1)
    set_vault(session, planet_id, metal=0, crystal=0, deuterium=0, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME)

    response = client.post(f"/planets/{planet_id}/research/plasma_technology/start")

    assert response.status_code == 409
    assert response.json()["detail"] == TECH_NOT_AVAILABLE


def test_start_research_with_insufficient_resources_changes_nothing(session: Session) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "research_lab", 1)
    # Energy technology 0 to 1 costs 800 crystal and 400 deuterium. One short of crystal.
    set_vault(session, planet_id, metal=0, crystal=799, deuterium=400, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME)

    response = client.post(f"/planets/{planet_id}/research/energy_technology/start")

    assert response.status_code == 409
    assert response.json()["detail"] == NOT_ENOUGH
    vault = client.get(f"/planets/{planet_id}/vault").json()
    assert (vault["metal"], vault["crystal"], vault["deuterium"]) == (0, 799, 400)
    assert "running" not in client.get("/research").json()


def test_start_research_four_reasons_have_four_different_details(session: Session) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_vault(session, planet_id, metal=0, crystal=0, deuterium=0, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME)

    no_lab = client.post(f"/planets/{planet_id}/research/energy_technology/start")

    set_building_level(session, planet_id, "research_lab", 1)
    set_vault(session, planet_id, metal=100000, crystal=100000, deuterium=100000)
    assert client.post(f"/planets/{planet_id}/research/energy_technology/start").status_code == 200
    running = client.post(f"/planets/{planet_id}/research/plasma_technology/start")

    register_and_login(client, "bob@example.com")
    [bob_planet] = client.get("/planets").json()
    bob_id = UUID(bob_planet["id"])
    set_building_level(session, bob_id, "research_lab", 1)
    set_vault(session, bob_id, metal=100000, crystal=100000, deuterium=100000)
    unavailable = client.post(f"/planets/{bob_id}/research/plasma_technology/start")

    register_and_login(client, "carol@example.com")
    [carol_planet] = client.get("/planets").json()
    carol_id = UUID(carol_planet["id"])
    set_building_level(session, carol_id, "research_lab", 1)
    set_vault(session, carol_id, metal=0, crystal=0, deuterium=0)
    poor = client.post(f"/planets/{carol_id}/research/energy_technology/start")

    details = {
        no_lab.json()["detail"],
        running.json()["detail"],
        unavailable.json()["detail"],
        poor.json()["detail"],
    }
    assert (no_lab.status_code, running.status_code, unavailable.status_code, poor.status_code) == (
        409,
        409,
        409,
        409,
    )
    assert len(details) == 4


# --- Completion on read (docs/adr/0117) ----------------------------------------------------


def test_a_research_that_finishes_changes_production_after_its_finish_time(
    session: Session,
) -> None:
    app, client = new_client(session)
    planet_id = home_planet(client)
    set_building_level(session, planet_id, "research_lab", 1)
    # Solar plant 1 makes 22 at E=0 and 24 at E=1. Metal mine 2 uses 24: factor
    # 22/24 before the research, 1 after it.
    set_building_level(session, planet_id, "solar_plant", 1)
    set_building_level(session, planet_id, "metal_mine", 2)
    set_vault(session, planet_id, metal=100, crystal=1000, deuterium=1000, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME)

    start = client.post(f"/planets/{planet_id}/research/energy_technology/start")
    assert start.status_code == 200
    finishes_at = datetime.fromisoformat(start.json()["research"]["running"]["finishes_at"])
    before = client.get(f"/planets/{planet_id}/vault").json()
    # floor(30 * 2 * 1.1^2 * 22/24) = floor(72.6 * 22/24) = floor(66.55) = 66.
    assert before["production_per_hour"]["metal"] == 30 + 66

    set_clock(app, finishes_at + timedelta(hours=1))
    after = client.get(f"/planets/{planet_id}/vault").json()

    assert after["production_per_hour"]["metal"] == 30 + 72
    # Old production for 1440 seconds (0.4 hours), then new production for 1 hour.
    at_finish = 100 + (30 + 66) * 1440 // 3600
    assert after["metal"] == at_finish + (30 + 72) * 1
    assert client.get("/research").json()["technologies"][0]["level"] == 1
    assert "running" not in client.get("/research").json()


def test_start_research_uses_the_production_stored_by_a_due_research_not_the_old_one(
    session: Session,
) -> None:
    """A regression test for issue #79.

    Plasma technology finishes at T. A second research starts at T + 10 hours,
    with no read of the vault or the research in between. The vault must add
    the old (pre-plasma) production up to T, then the new (post-plasma)
    production from T to T + 10 hours, before it subtracts the cost. Before
    the fix, `start_research` used the vault rows from before
    `_complete_due_research_locked` ran, so the whole period used the new
    production.
    """
    app, client = new_client(session)
    planet_id = home_planet(client)
    user_id = user_id_of(session, "ada@example.com")
    set_building_level(session, planet_id, "research_lab", 1)
    set_building_level(session, planet_id, "solar_plant", 2)
    set_building_level(session, planet_id, "metal_mine", 2)
    set_building_level(session, planet_id, "metal_storage", 10)
    set_building_level(session, planet_id, "crystal_storage", 10)
    set_building_level(session, planet_id, "deuterium_tank", 10)
    set_technology_level(session, user_id, "energy_technology", 1)
    set_vault(session, planet_id, metal=10000, crystal=10000, deuterium=10000, updated_at=BASE_TIME)
    set_clock(app, BASE_TIME)

    start_plasma = client.post(f"/planets/{planet_id}/research/plasma_technology/start")
    assert start_plasma.status_code == 200
    finishes_at = datetime.fromisoformat(start_plasma.json()["research"]["running"]["finishes_at"])
    # 3600 * (2000 + 4000) / 1000 / (1 + 1) = 10800 seconds = 3 hours.
    assert finishes_at == BASE_TIME + timedelta(hours=3)

    # No read of the vault or the research happens between the finish and the
    # next start.
    set_clock(app, finishes_at + timedelta(hours=10))
    response = client.post(f"/planets/{planet_id}/research/energy_technology/start")

    assert response.status_code == 200
    body = response.json()
    # Metal mine 2: floor(30 * 2 * 1.1^2) = floor(72.6) = 72 at plasma 0, 73 at plasma 1.
    # 10000 - 2000 (the plasma cost), then 3 hours at the old production (30 + 72),
    # then 10 hours at the new one (30 + 73).
    metal_at_finish = 10000 - 2000 + (30 + 72) * 3
    metal_after = metal_at_finish + (30 + 73) * 10
    # Crystal has no mine, so its production does not depend on the technology:
    # 10000 - 4000 (the plasma cost) + 15 * 13 hours - 1600 (the energy cost, level 1).
    crystal_after = 10000 - 4000 + 15 * 13 - 1600
    # Deuterium: 10000 - 1000 (the plasma cost) - 800 (the energy cost, level 1).
    deuterium_after = 10000 - 1000 - 800
    assert body["vault"]["metal"] == metal_after
    assert body["vault"]["crystal"] == crystal_after
    assert body["vault"]["deuterium"] == deuterium_after
    assert body["research"]["technologies"][1]["kind"] == "plasma_technology"
    assert body["research"]["technologies"][1]["level"] == 1
    assert body["research"]["running"]["kind"] == "energy_technology"


def _due_building_and_research(
    session: Session, client: TestClient, email: str
) -> tuple[UUID, UUID]:
    """A planet with a research due at BASE_TIME + 1h and a building upgrade due
    an hour later, both before the clock that `start_research` reads."""
    planet_id = home_planet(client, email)
    user_id = user_id_of(session, email)
    set_building_level(session, planet_id, "research_lab", 1)
    set_building_level(session, planet_id, "solar_plant", 2)
    set_building_level(session, planet_id, "metal_mine", 2)
    set_vault(session, planet_id, metal=10000, crystal=10000, deuterium=10000, updated_at=BASE_TIME)
    session.add(
        ResearchRow(
            user_id=user_id,
            kind="energy_technology",
            planet_id=planet_id,
            finishes_at=BASE_TIME + timedelta(hours=1),
        )
    )
    session.add(
        ConstructionRow(
            planet_id=planet_id, kind="metal_mine", finishes_at=BASE_TIME + timedelta(hours=2)
        )
    )
    session.commit()
    return planet_id, user_id


def test_start_research_with_a_due_building_and_a_due_research_matches_a_read_before_the_start(
    session: Session,
) -> None:
    direct_app, direct_client = new_client(session)
    direct_planet_id, _ = _due_building_and_research(session, direct_client, "ada@example.com")
    set_clock(direct_app, BASE_TIME + timedelta(hours=5))

    direct = direct_client.post(f"/planets/{direct_planet_id}/research/energy_technology/start")

    with_read_app, with_read_client = new_client(session)
    with_read_planet_id, _ = _due_building_and_research(
        session, with_read_client, "bob@example.com"
    )
    set_clock(with_read_app, BASE_TIME + timedelta(hours=5))
    with_read_client.get(f"/planets/{with_read_planet_id}/vault")

    with_read = with_read_client.post(
        f"/planets/{with_read_planet_id}/research/energy_technology/start"
    )

    assert direct.status_code == 200
    assert with_read.status_code == 200
    direct_vault = direct.json()["vault"]
    with_read_vault = with_read.json()["vault"]
    assert (direct_vault["metal"], direct_vault["crystal"], direct_vault["deuterium"]) == (
        with_read_vault["metal"],
        with_read_vault["crystal"],
        with_read_vault["deuterium"],
    )
    assert direct_vault["production_per_hour"] == with_read_vault["production_per_hour"]
    direct_research = direct.json()["research"]
    with_read_research = with_read.json()["research"]
    assert direct_research["technologies"] == with_read_research["technologies"]
    assert direct_research["running"]["kind"] == with_read_research["running"]["kind"]
    assert direct_research["running"]["finishes_at"] == with_read_research["running"]["finishes_at"]
