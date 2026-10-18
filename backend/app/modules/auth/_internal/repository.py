from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth._internal.models import EmailTakenError, User
from app.shared.orm.users import UserRow


def _to_user(row: UserRow) -> User:
    return User(id=row.id, email=row.email, password_hash=row.password_hash)


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        row = self._session.get(UserRow, user_id)
        return _to_user(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        row = self._session.scalars(select(UserRow).where(UserRow.email == email)).one_or_none()
        return _to_user(row) if row else None

    def add(self, email: str, password_hash: str) -> User:
        row = UserRow(email=email, password_hash=password_hash)
        try:
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError as error:
            raise EmailTakenError from error
        self._session.commit()
        return _to_user(row)
