from sqlalchemy import text
from sqlalchemy.orm import Session

from app.shared.orm import UserRow


def test_database_answers(session: Session) -> None:
    assert session.execute(text("select 1")).scalar_one() == 1


def test_users_table_exists(session: Session) -> None:
    session.add(UserRow(email="fixture@example.com", password_hash="x"))
    session.flush()

    assert session.query(UserRow).filter_by(email="fixture@example.com").count() == 1


def test_the_rollback_removed_the_user(session: Session) -> None:
    assert session.query(UserRow).filter_by(email="fixture@example.com").count() == 0


def test_tests_use_their_own_database(session: Session) -> None:
    assert session.execute(text("select current_database()")).scalar_one().endswith("_test")
