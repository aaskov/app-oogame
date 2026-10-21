from uuid import UUID

from app.modules.planets._internal.models import Planet, Vault
from app.modules.planets._internal.repository import PlanetRepository


class PlanetService:
    def __init__(self, repository: PlanetRepository) -> None:
        self._repository = repository

    def list_planets(self, user_id: UUID) -> list[Planet]:
        planets = self._repository.list_for_user(user_id)
        if planets:
            return planets
        self._repository.create_home_planet(user_id)
        return self._repository.list_for_user(user_id)

    def read_vault(self, planet_id: UUID, user_id: UUID) -> Vault | None:
        return self._repository.get_vault(planet_id, user_id)
