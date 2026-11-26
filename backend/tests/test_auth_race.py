"""Two registrations with the same username at the same time: only one succeeds (docs/adr/0118).

The same set-up as test_planets_building_upgrade_race.py: two real database
connections race for the same unique username, so this test commits its own
rows and cleans them up itself.
"""

import threading
from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.main import create_app
from app.shared.db import get_engine, get_session
from app.shared.orm.users import UserRow

USERNAME = "racer"


def test_two_registrations_with_the_same_username_at_the_same_time_only_one_succeeds() -> None:
    engine = get_engine()
    app = create_app()

    def session_per_request() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_per_request

    statuses: list[int] = []
    barrier = threading.Barrier(2)

    def register(email: str) -> None:
        barrier.wait()
        with TestClient(app) as client:
            response = client.post(
                "/auth/register",
                json={"email": email, "password": "correct horse", "username": USERNAME},
            )
        statuses.append(response.status_code)

    threads = [
        threading.Thread(target=register, args=(email,))
        for email in ("racer-a@example.com", "racer-b@example.com")
    ]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert sorted(statuses) == [201, 409]

        check = Session(engine)
        try:
            count = check.scalar(select(func.count(UserRow.id)).where(UserRow.username == USERNAME))
            assert count == 1
        finally:
            check.close()
    finally:
        cleanup = Session(engine)
        try:
            cleanup.execute(delete(UserRow).where(UserRow.username == USERNAME))
            cleanup.commit()
        finally:
            cleanup.close()
