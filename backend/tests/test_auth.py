from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.config import get_settings
from app.shared.orm.users import UserRow

EMAIL = "ada@example.com"
PASSWORD = "correct horse"
UNKNOWN_OR_WRONG = "Invalid email or password"


def register(client: TestClient, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/auth/register", json={"email": email, "password": password})


def login(client: TestClient, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def make_token(
    sub: str,
    *,
    secret: str | None = None,
    expires_in: timedelta = timedelta(minutes=5),
) -> str:
    settings = get_settings()
    payload = {"sub": sub, "exp": datetime.now(UTC) + expires_in}
    return jwt.encode(payload, secret or settings.jwt_secret, algorithm="HS256")


def set_session_cookie(client: TestClient, token: str) -> None:
    client.cookies.set(get_settings().session_cookie_name, token)


# --- register ---------------------------------------------------------------


def test_register_returns_201_and_the_user(client: TestClient) -> None:
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email"}
    assert UUID(body["id"])
    assert body["email"] == EMAIL


def test_register_stores_an_argon2_hash_never_the_password(
    client: TestClient, session: Session
) -> None:
    register(client)

    row = session.scalars(select(UserRow).where(UserRow.email == EMAIL)).one()
    assert row.password_hash.startswith("$argon2")
    assert PASSWORD not in row.password_hash


def test_register_returns_409_with_detail_if_the_email_exists(client: TestClient) -> None:
    register(client)

    response = register(client)

    assert response.status_code == 409
    assert isinstance(response.json()["detail"], str)


def test_register_email_comparison_ignores_case(client: TestClient) -> None:
    register(client, email="Ada@Example.com")

    response = register(client, email="ada@EXAMPLE.com")

    assert response.status_code == 409


@pytest.mark.parametrize("email", ["not-an-email", "ada@", "", "a" * 320 + "@example.com"])
def test_register_returns_422_for_an_invalid_email(client: TestClient, email: str) -> None:
    assert register(client, email=email).status_code == 422


@pytest.mark.parametrize("password", ["", "1234567", "x" * 129])
def test_register_returns_422_for_a_password_outside_8_to_128(
    client: TestClient, password: str
) -> None:
    assert register(client, password=password).status_code == 422


@pytest.mark.parametrize("password", ["12345678", "x" * 128])
def test_register_accepts_the_password_length_limits(client: TestClient, password: str) -> None:
    assert register(client, password=password).status_code == 201


def test_register_does_not_log_the_user_in(client: TestClient) -> None:
    response = register(client)

    assert "set-cookie" not in response.headers


# --- login ------------------------------------------------------------------


def test_login_returns_200_and_the_user(client: TestClient) -> None:
    user = register(client).json()

    response = login(client)

    assert response.status_code == 200
    assert response.json() == user


def test_login_email_comparison_ignores_case(client: TestClient) -> None:
    register(client)

    assert login(client, email="ADA@example.com").status_code == 200


def test_login_sets_the_session_cookie_with_the_required_attributes(client: TestClient) -> None:
    settings = get_settings()
    register(client)

    response = login(client)

    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{settings.session_cookie_name}=")
    attributes = [part.strip().lower() for part in cookie.split(";")[1:]]
    assert "httponly" in attributes
    assert "samesite=lax" in attributes
    assert "path=/" in attributes
    assert ("secure" in attributes) is settings.session_cookie_secure


def test_login_cookie_holds_a_jwt_for_the_user(client: TestClient) -> None:
    settings = get_settings()
    user = register(client).json()

    login(client)

    token = client.cookies[settings.session_cookie_name]
    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert claims["sub"] == user["id"]
    expected = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)
    assert abs(claims["exp"] - expected.timestamp()) < 60


def test_login_returns_401_with_the_same_detail_for_unknown_email_and_wrong_password(
    client: TestClient,
) -> None:
    register(client)

    unknown = login(client, email="nobody@example.com")
    wrong = login(client, password="not the password")

    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": UNKNOWN_OR_WRONG}
    assert "set-cookie" not in unknown.headers
    assert "set-cookie" not in wrong.headers


# --- logout -----------------------------------------------------------------


def test_logout_returns_204_and_clears_the_cookie(client: TestClient) -> None:
    name = get_settings().session_cookie_name
    register(client)
    login(client)
    assert name in client.cookies

    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert response.content == b""
    assert name not in client.cookies
    assert client.get("/auth/me").status_code == 401


def test_logout_without_a_session_returns_204_and_clears_the_cookie(client: TestClient) -> None:
    response = client.post("/auth/logout")

    assert response.status_code == 204
    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith(f"{get_settings().session_cookie_name}=")
    assert "max-age=0" in cookie


# --- me ---------------------------------------------------------------------


def test_me_returns_200_and_the_user_for_a_valid_session(client: TestClient) -> None:
    user = register(client).json()
    login(client)

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json() == user


def test_me_returns_401_without_a_cookie(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert isinstance(response.json()["detail"], str)


def test_me_returns_401_for_an_expired_jwt(client: TestClient) -> None:
    user = register(client).json()
    set_session_cookie(client, make_token(user["id"], expires_in=timedelta(minutes=-1)))

    assert client.get("/auth/me").status_code == 401


def test_me_returns_401_for_a_bad_signature(client: TestClient) -> None:
    user = register(client).json()
    set_session_cookie(client, make_token(user["id"], secret="x" * 32))

    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("token", ["garbage", "a.b.c"])
def test_me_returns_401_for_a_malformed_jwt(client: TestClient, token: str) -> None:
    set_session_cookie(client, token)

    assert client.get("/auth/me").status_code == 401


def test_me_returns_401_if_sub_is_not_a_user_id(client: TestClient) -> None:
    set_session_cookie(client, make_token("not-a-uuid"))

    assert client.get("/auth/me").status_code == 401


def test_me_returns_401_for_a_deleted_user(client: TestClient, session: Session) -> None:
    register(client)
    login(client)
    session.delete(session.scalars(select(UserRow)).one())
    session.flush()

    assert client.get("/auth/me").status_code == 401


def test_me_returns_401_for_a_valid_jwt_of_an_unknown_user(client: TestClient) -> None:
    set_session_cookie(client, make_token(str(uuid4())))

    assert client.get("/auth/me").status_code == 401
