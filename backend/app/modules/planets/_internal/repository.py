from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.planets._internal.models import Construction, Planet, StoredVault
from app.shared.orm.buildings import BuildingRow
from app.shared.orm.constructions import ConstructionRow
from app.shared.orm.planets import HOME_PLANET_NAME, PlanetRow
from app.shared.orm.vaults import START_CRYSTAL, START_DEUTERIUM, START_METAL, VaultRow


def _to_planet(row: PlanetRow) -> Planet:
    return Planet(id=row.id, name=row.name)


def _to_stored_vault(row: VaultRow) -> StoredVault:
    return StoredVault(
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

    def get_vault(self, planet_id: UUID, user_id: UUID) -> StoredVault | None:
        row = self._session.scalars(
            select(VaultRow)
            .join(PlanetRow, PlanetRow.id == VaultRow.planet_id)
            .where(VaultRow.planet_id == planet_id, PlanetRow.user_id == user_id)
        ).one_or_none()
        return _to_stored_vault(row) if row else None

    def lock_vault(self, planet_id: UUID, user_id: UUID) -> StoredVault | None:
        """Return the vault with a row lock (SELECT ... FOR UPDATE, docs/adr/0111).

        The lock belongs to the current transaction. The caller commits or
        rolls back to release it.
        """
        row = self._session.scalars(
            select(VaultRow)
            .join(PlanetRow, PlanetRow.id == VaultRow.planet_id)
            .where(VaultRow.planet_id == planet_id, PlanetRow.user_id == user_id)
            .with_for_update(of=VaultRow)
        ).one_or_none()
        return _to_stored_vault(row) if row else None

    def planet_owned_by(self, planet_id: UUID, user_id: UUID) -> bool:
        return (
            self._session.scalars(
                select(PlanetRow.id).where(PlanetRow.id == planet_id, PlanetRow.user_id == user_id)
            ).one_or_none()
            is not None
        )

    def get_building_levels(self, planet_id: UUID) -> dict[str, int]:
        rows = self._session.scalars(select(BuildingRow).where(BuildingRow.planet_id == planet_id))
        return {row.kind: row.level for row in rows}

    def update_vault_amounts(
        self, planet_id: UUID, metal: int, crystal: int, deuterium: int, at: datetime
    ) -> None:
        self._session.execute(
            update(VaultRow)
            .where(VaultRow.planet_id == planet_id)
            .values(metal=metal, crystal=crystal, deuterium=deuterium, updated_at=at)
        )

    def set_building_level(self, planet_id: UUID, kind: str, level: int) -> None:
        statement = (
            insert(BuildingRow)
            .values(planet_id=planet_id, kind=kind, level=level)
            .on_conflict_do_update(
                index_elements=["planet_id", "kind"],
                set_={"level": level},
            )
        )
        self._session.execute(statement)

    def get_construction(self, planet_id: UUID) -> Construction | None:
        # populate_existing: after the vault lock, read what the other request committed.
        row = self._session.scalars(
            select(ConstructionRow)
            .where(ConstructionRow.planet_id == planet_id)
            .execution_options(populate_existing=True)
        ).one_or_none()
        return Construction(kind=row.kind, finishes_at=row.finishes_at) if row else None

    def add_construction(self, planet_id: UUID, kind: str, finishes_at: datetime) -> None:
        self._session.add(ConstructionRow(planet_id=planet_id, kind=kind, finishes_at=finishes_at))
        self._session.flush()

    def delete_construction(self, planet_id: UUID) -> None:
        self._session.execute(delete(ConstructionRow).where(ConstructionRow.planet_id == planet_id))

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
