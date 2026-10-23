"""Two reads of a due upgrade complete it exactly once (docs/adr/0114).

The same set-up as test_planets_building_upgrade_race.py: two real database
connections, so this test commits its own rows and cleans them up itself. A
short, test-only delay right after the lock is taken makes one request really
wait for the lock of the other. Without the second read of the construction
row after the lock, both requests would raise the level.
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
from app.modules.planets._internal.models import StoredVault
from app.modules.planets._internal.repository import PlanetRepository
from app.shared.db import get_engine, get_session
from app.shared.orm.buildings import BuildingRow
from app.shared.orm.constructions import ConstructionRow
from app.shared.orm.planets import PlanetRow
from app.shared.orm.users import UserRow
from app.shared.orm.vaults import VaultRow


@pytest.mark.parametrize("path", ["vault", "buildings"])
def test_two_reads_after_the_finish_time_raise_the_level_by_exactly_one(
    monkeypatch: pytest.MonkeyPatch, path: str
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
    two_hours_ago = datetime.now(UTC) - timedelta(hours=2)

    setup = Session(engine)
    try:
        setup.add(UserRow(id=user_id, email=f"{uuid4()}@example.com", password_hash="x"))
        setup.flush()
        setup.add(PlanetRow(id=planet_id, user_id=user_id, name="Homeworld", is_home=True))
        setup.flush()
        setup.add(
            VaultRow(planet_id=planet_id, metal=0, crystal=0, deuterium=0, updated_at=two_hours_ago)
        )
        setup.add(BuildingRow(planet_id=planet_id, kind="metal_mine", level=3))
        setup.add(
            ConstructionRow(
                planet_id=planet_id,
                kind="metal_mine",
                finishes_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        setup.commit()
    finally:
        setup.close()

    app = create_app()
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    def session_per_request() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_per_request

    statuses: list[int] = []
    barrier = threading.Barrier(2)

    def read() -> None:
        barrier.wait()
        with TestClient(app) as client:
            response = client.get(f"/planets/{planet_id}/{path}")
        statuses.append(response.status_code)

    threads = [threading.Thread(target=read) for _ in range(2)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert statuses == [200, 200]

        check = Session(engine)
        try:
            building = check.get(BuildingRow, (planet_id, "metal_mine"))
            assert building is not None
            assert building.level == 4
            assert check.get(ConstructionRow, planet_id) is None
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
