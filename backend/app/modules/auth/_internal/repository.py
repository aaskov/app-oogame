from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth._internal.models import EmailTakenError, User, UsernameTakenError
from app.shared.orm.users import UserRow

# The name of the unique constraint on users.username (the migration of
# docs/adr/0118), used to tell a username conflict from an email conflict.
_USERNAME_CONSTRAINT = "users_username_key"


def _to_user(row: UserRow) -> User:
    # Nullable only until the backend sets it for each new row (docs/adr/0118).
    assert row.username is not None
    return User(id=row.id, email=row.email, username=row.username, password_hash=row.password_hash)


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        row = self._session.get(UserRow, user_id)
        return _to_user(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        row = self._session.scalars(select(UserRow).where(UserRow.email == email)).one_or_none()
        return _to_user(row) if row else None

    def get_by_username(self, username: str) -> User | None:
        row = self._session.scalars(
            select(UserRow).where(UserRow.username == username)
        ).one_or_none()
        return _to_user(row) if row else None

    def add(self, email: str, username: str, password_hash: str) -> User:
        row = UserRow(email=email, username=username, password_hash=password_hash)
        try:
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError as error:
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if constraint == _USERNAME_CONSTRAINT:
                raise UsernameTakenError from error
            raise EmailTakenError from error
        self._session.commit()
        return _to_user(row)
