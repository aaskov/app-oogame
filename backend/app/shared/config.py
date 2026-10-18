"""Settings from the environment (docs/adr/0104, 0105). Architect-owned (CODEOWNERS)."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    jwt_expires_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:3000"]
    session_cookie_name: str = "session"
    session_cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue] -- the values come from the environment.
