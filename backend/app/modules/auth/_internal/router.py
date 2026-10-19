from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app.modules.auth._internal.dependencies import get_auth_service, get_current_user
from app.modules.auth._internal.models import EmailTakenError, User
from app.modules.auth._internal.schemas import Credentials, ErrorOut, UserOut
from app.modules.auth._internal.service import AuthService
from app.shared.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

ServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post(
    "/register",
    operation_id="register",
    status_code=201,
    response_model=UserOut,
    responses={409: {"model": ErrorOut}, 422: {}},
)
def register(credentials: Credentials, service: ServiceDep) -> User:
    try:
        return service.register(credentials.email, credentials.password)
    except EmailTakenError:
        raise HTTPException(status_code=409, detail="Email already registered") from None


@router.post(
    "/login",
    operation_id="login",
    response_model=UserOut,
    responses={401: {"model": ErrorOut}, 422: {}},
)
def login(
    credentials: Credentials,
    response: Response,
    service: ServiceDep,
    settings: SettingsDep,
) -> User:
    user = service.authenticate(credentials.email, credentials.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    response.set_cookie(
        settings.session_cookie_name,
        service.issue_token(user),
        max_age=settings.jwt_expires_minutes * 60,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )
    return user


@router.post("/logout", operation_id="logout", status_code=204)
def logout(response: Response, settings: SettingsDep) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )


@router.get(
    "/me",
    operation_id="read_me",
    response_model=UserOut,
    responses={401: {"model": ErrorOut}},
)
def read_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user
