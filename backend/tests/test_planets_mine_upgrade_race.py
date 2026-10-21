"""Two upgrades at the same time cannot spend the same resources (docs/adr/0111).

This test needs two real database connections racing for the same vault row.
The `client`/`session` fixtures in conftest.py share one connection whose outer
transaction is never committed (so tests roll back and stay isolated from each
other). A second, genuinely separate connection could not see any row created
through that transaction. So this test commits its own rows directly, with its
own engine-backed sessions, and cleans them up itself afterward.

Both requests reach their SELECT ... FOR UPDATE within microseconds of each
other, which does not reliably force one to actually wait on the other's lock.
So the test widens that window with a short, test-only delay right after the
lock is taken, while it is still held.
"""

import threading
import time
from collections.abc import Iterator
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
from app.shared.orm.planets import PlanetRow
from app.shared.orm.users import UserRow
from app.shared.orm.vaults import VaultRow

# Enough for exactly one upgrade of metal_mine from level 0 (docs/adr/0111).
METAL_MINE_LEVEL_0_COST = {"metal": 60, "crystal": 15, "deuterium": 0}


def test_two_upgrades_at_the_same_time_only_one_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
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
        setup.add(VaultRow(planet_id=planet_id, **METAL_MINE_LEVEL_0_COST))
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

    def upgrade() -> None:
        barrier.wait()
        with TestClient(app) as client:
            response = client.post(f"/planets/{planet_id}/mines/metal_mine/upgrade")
        statuses.append(response.status_code)

    threads = [threading.Thread(target=upgrade) for _ in range(2)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert sorted(statuses) == [200, 409]

        check = Session(engine)
        try:
            vault = check.get(VaultRow, planet_id)
            assert vault is not None
            assert vault.metal == 0
            assert vault.crystal == 0
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
