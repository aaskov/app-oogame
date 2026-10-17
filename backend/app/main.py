"""The FastAPI app. It mounts the router of each module from its public_api."""

from fastapi import FastAPI

from app.modules.health import public_api as health


def create_app() -> FastAPI:
    app = FastAPI(title="app-oogame")
    app.include_router(health.router)
    return app


app = create_app()
