from app.shared.db import connect


def test_database_answers() -> None:
    with connect() as connection:
        row = connection.execute("select 1").fetchone()

    assert row == (1,)
