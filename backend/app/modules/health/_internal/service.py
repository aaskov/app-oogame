from app.modules.health._internal.schemas import Health


class HealthService:
    def get_health(self) -> Health:
        return Health(status="ok")


def get_health_service() -> HealthService:
    return HealthService()
