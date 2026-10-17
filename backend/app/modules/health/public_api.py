"""The only part of the health module that other modules and app.main can import."""

from app.modules.health._internal.router import router

__all__ = ["router"]
