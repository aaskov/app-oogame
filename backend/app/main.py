"""The FastAPI app. Architect-owned (CODEOWNERS).

It mounts the router of each module from its public_api.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.auth import public_api as auth
from app.modules.health import public_api as health
from app.modules.planets import public_api as planets
from app.shared.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="app-oogame")
    # The frontend sends the session cookie, so CORS allows credentials (docs/adr/0105).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(planets.router)
    return app


app = create_app()
