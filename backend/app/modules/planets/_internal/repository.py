from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.planets._internal.models import Planet, Vault
from app.shared.orm.planets import HOME_PLANET_NAME, PlanetRow
from app.shared.orm.vaults import START_CRYSTAL, START_DEUTERIUM, START_METAL, VaultRow


def _to_planet(row: PlanetRow) -> Planet:
    return Planet(id=row.id, name=row.name)


def _to_vault(row: VaultRow) -> Vault:
    return Vault(
        planet_id=row.planet_id,
        metal=row.metal,
        crystal=row.crystal,
        deuterium=row.deuterium,
        updated_at=row.updated_at,
    )


class PlanetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(self, user_id: UUID) -> list[Planet]:
        rows = self._session.scalars(
            select(PlanetRow).where(PlanetRow.user_id == user_id).order_by(PlanetRow.created_at)
        )
        return [_to_planet(row) for row in rows]

    def create_home_planet(self, user_id: UUID) -> None:
        """Create "Homeworld" and its vault, unless the user already has one.

        Uses INSERT ... ON CONFLICT DO NOTHING on the partial unique index, so
        two first requests at the same time cannot create two home planets
        (docs/adr/0109).
        """
        statement = (
            insert(PlanetRow)
            .values(id=uuid4(), user_id=user_id, name=HOME_PLANET_NAME, is_home=True)
            .on_conflict_do_nothing(index_elements=["user_id"], index_where=text("is_home"))
            .returning(PlanetRow.id)
        )
        created_id = self._session.scalars(statement).one_or_none()
        if created_id is not None:
            self._session.add(
                VaultRow(
                    planet_id=created_id,
                    metal=START_METAL,
                    crystal=START_CRYSTAL,
                    deuterium=START_DEUTERIUM,
                )
            )
        self._session.commit()

    def get_vault(self, planet_id: UUID, user_id: UUID) -> Vault | None:
        row = self._session.scalars(
            select(VaultRow)
            .join(PlanetRow, PlanetRow.id == VaultRow.planet_id)
            .where(VaultRow.planet_id == planet_id, PlanetRow.user_id == user_id)
        ).one_or_none()
        return _to_vault(row) if row else None

    def update_vault(
        self,
        planet_id: UUID,
        user_id: UUID,
        *,
        metal: int | None,
        crystal: int | None,
        deuterium: int | None,
    ) -> Vault | None:
        row = self._session.scalars(
            select(VaultRow)
            .join(PlanetRow, PlanetRow.id == VaultRow.planet_id)
            .where(VaultRow.planet_id == planet_id, PlanetRow.user_id == user_id)
        ).one_or_none()
        if row is None:
            return None
        if metal is not None:
            row.metal = metal
        if crystal is not None:
            row.crystal = crystal
        if deuterium is not None:
            row.deuterium = deuterium
        self._session.commit()
        self._session.refresh(row)
        return _to_vault(row)
