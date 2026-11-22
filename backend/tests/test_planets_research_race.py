"""Two reads of a due research raise the technology level exactly once (docs/adr/0117).

The same set-up as test_planets_building_upgrade_race.py: two real database
connections, so this test commits its own rows and cleans them up itself. A
short, test-only delay right after the vault lock is taken makes one request
really wait for the lock of the other. Without the second read of the
research row after the locks, both requests would raise the level.
"""

import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.main import create_app
from app.modules.auth.public_api import get_current_user_id
from app.modules.planets._internal.dependencies import get_current_time
from app.modules.planets._internal.models import StoredVault
from app.modules.planets._internal.repository import PlanetRepository
from app.shared.db import get_engine, get_session
from app.shared.orm.buildings import BuildingRow
from app.shared.orm.planets import PlanetRow
from app.shared.orm.research import ResearchRow, TechnologyRow
from app.shared.orm.users import UserRow
from app.shared.orm.vaults import VaultRow

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def test_two_reads_after_a_research_is_due_raise_the_level_by_exactly_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_lock_vault = PlanetRepository.lock_vault

    def lock_vault_and_hold(
        self: PlanetRepository, planet_id: UUID, user_id: UUID
    ) -> StoredVault | None:
        vault = original_lock_vault(self, planet_id, user_id)
        time.sleep(0.2)
        return vault

    monkeypatch.setattr(PlanetRepository, "lock_vault", lock_vault_and_hold)

    engine = get_engine()
    user_id = uuid4()
    planet_id = uuid4()

    setup = Session(engine)
    try:
        setup.add(UserRow(id=user_id, email=f"{uuid4()}@example.com", password_hash="x"))
        setup.flush()
        setup.add(PlanetRow(id=planet_id, user_id=user_id, name="Homeworld", is_home=True))
        setup.flush()
        setup.add(
            VaultRow(
                planet_id=planet_id,
                metal=1000,
                crystal=1000,
                deuterium=1000,
                updated_at=BASE_TIME,
            )
        )
        setup.add(BuildingRow(planet_id=planet_id, kind="research_lab", level=1))
        setup.add(
            ResearchRow(
                user_id=user_id,
                kind="energy_technology",
                planet_id=planet_id,
                finishes_at=BASE_TIME,
            )
        )
        setup.commit()
    finally:
        setup.close()

    app = create_app()
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_current_time] = lambda: BASE_TIME + timedelta(hours=1)

    def session_per_request() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_per_request

    barrier = threading.Barrier(2)

    def read() -> None:
        barrier.wait()
        with TestClient(app) as client:
            client.get(f"/planets/{planet_id}/vault")

    threads = [threading.Thread(target=read) for _ in range(2)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        check = Session(engine)
        try:
            technology = check.get(TechnologyRow, (user_id, "energy_technology"))
            assert technology is not None
            assert technology.level == 1
            assert check.get(ResearchRow, user_id) is None
        finally:
            check.close()
    finally:
        cleanup = Session(engine)
        try:
            cleanup.execute(delete(PlanetRow).where(PlanetRow.id == planet_id))
            cleanup.execute(delete(UserRow).where(UserRow.id == user_id))
            cleanup.commit()
        finally:
            cleanup.close()
