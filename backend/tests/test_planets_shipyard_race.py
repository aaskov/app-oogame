"""Two reads of due ships add them exactly once (docs/adr/0115).

The same set-up as test_planets_building_upgrade_race.py: two real database
connections, so this test commits its own rows and cleans them up itself. A
short, test-only delay right after the lock is taken makes one request really
wait for the lock of the other. Without the second read of the order row after
the lock, both requests would add the same ships.
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
from app.shared.orm.planets import PlanetRow
from app.shared.orm.ships import ShipOrderRow, ShipRow
from app.shared.orm.users import UserRow
from app.shared.orm.vaults import VaultRow


def test_two_reads_after_a_ship_is_due_add_exactly_the_due_ships(
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
    now = datetime.now(UTC)

    setup = Session(engine)
    try:
        setup.add(UserRow(id=user_id, email=f"{uuid4()}@example.com", password_hash="x"))
        setup.flush()
        setup.add(PlanetRow(id=planet_id, user_id=user_id, name="Homeworld", is_home=True))
        setup.flush()
        setup.add(VaultRow(planet_id=planet_id, metal=0, crystal=0, deuterium=0, updated_at=now))
        setup.add(BuildingRow(planet_id=planet_id, kind="shipyard", level=1))
        setup.add(ShipRow(planet_id=planet_id, kind="small_cargo", count=10))
        # 5 ships remain. Exactly 2 are due (450 and 150 s ago). The third is 150 s ahead.
        setup.add(
            ShipOrderRow(
                planet_id=planet_id,
                kind="small_cargo",
                remaining=5,
                seconds_per_ship=300,
                next_finishes_at=now - timedelta(seconds=450),
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
            response = client.get(f"/planets/{planet_id}/ships")
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
            ships = check.get(ShipRow, (planet_id, "small_cargo"))
            assert ships is not None
            assert ships.count == 12
            order = check.get(ShipOrderRow, planet_id)
            assert order is not None
            assert order.remaining == 3
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
