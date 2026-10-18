from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.modules.auth._internal.models import EmailTakenError, User
from app.modules.auth._internal.repository import UserRepository
from app.shared.config import Settings

_ALGORITHM = "HS256"
_password_hash = PasswordHash.recommended()
# Verified against when the email is unknown, so both login failures take the same time.
_DUMMY_HASH = _password_hash.hash("dummy password")


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, repository: UserRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    def register(self, email: str, password: str) -> User:
        email = normalize_email(email)
        if self._repository.get_by_email(email):
            raise EmailTakenError
        return self._repository.add(email, _password_hash.hash(password))

    def authenticate(self, email: str, password: str) -> User | None:
        user = self._repository.get_by_email(normalize_email(email))
        if user is None:
            _password_hash.verify(password, _DUMMY_HASH)
            return None
        if not _password_hash.verify(password, user.password_hash):
            return None
        return user

    def issue_token(self, user: User) -> str:
        expires = datetime.now(UTC) + timedelta(minutes=self._settings.jwt_expires_minutes)
        claims = {"sub": str(user.id), "exp": expires}
        return jwt.encode(claims, self._settings.jwt_secret, algorithm=_ALGORITHM)

    def user_from_token(self, token: str) -> User | None:
        try:
            claims = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[_ALGORITHM],
                options={"require": ["exp", "sub"]},
            )
            user_id = UUID(claims["sub"])
        except (jwt.InvalidTokenError, ValueError):
            return None
        return self._repository.get_by_id(user_id)
