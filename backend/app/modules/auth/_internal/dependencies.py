from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.modules.auth._internal.models import User
from app.modules.auth._internal.repository import UserRepository
from app.modules.auth._internal.service import AuthService
from app.shared.config import Settings, get_settings
from app.shared.db import get_session


def get_auth_service(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(UserRepository(session), settings)


def get_current_user(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    user = service.user_from_token(token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
