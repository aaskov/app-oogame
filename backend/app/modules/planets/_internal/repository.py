from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.planets._internal.models import (
    Construction,
    Coordinates,
    Planet,
    ShipKind,
    StoredResearch,
    StoredShipOrder,
    StoredVault,
    TechKind,
)
from app.shared.orm.buildings import BuildingRow
from app.shared.orm.constructions import ConstructionRow
from app.shared.orm.planets import HOME_PLANET_NAME, PlanetRow
from app.shared.orm.research import ResearchRow, TechnologyRow
from app.shared.orm.ships import ShipOrderRow, ShipRow
from app.shared.orm.users import UserRow
from app.shared.orm.vaults import START_CRYSTAL, START_DEUTERIUM, START_METAL, VaultRow


def _to_planet(row: PlanetRow) -> Planet:
    # Nullable only until the backend sets them for each new row (docs/adr/0118).
    assert row.galaxy is not None
    assert row.system is not None
    assert row.position is not None
    return Planet(
        id=row.id,
        name=row.name,
        coordinates=Coordinates(galaxy=row.galaxy, system=row.system, position=row.position),
    )


def _to_stored_vault(row: VaultRow) -> StoredVault:
    return StoredVault(
        planet_id=row.planet_id,
        metal=row.metal,
        crystal=row.crystal,
        deuterium=row.deuterium,
        updated_at=row.updated_at,
    )


def _to_ship_kind(kind: str) -> ShipKind:
    # The check constraint known_kind allows only these two values.
    return "small_cargo" if kind == "small_cargo" else "light_fighter"


def _to_tech_kind(kind: str) -> TechKind:
    # The check constraint known_kind allows only these two values.
    return "energy_technology" if kind == "energy_technology" else "plasma_technology"


class PlanetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(self, user_id: UUID) -> list[Planet]:
        rows = self._session.scalars(
            select(PlanetRow).where(PlanetRow.user_id == user_id).order_by(PlanetRow.created_at)
        )
        return [_to_planet(row) for row in rows]

    def home_planet_exists(self, user_id: UUID) -> bool:
        return (
            self._session.scalars(
                select(PlanetRow.id).where(PlanetRow.user_id == user_id, PlanetRow.is_home)
            ).one_or_none()
            is not None
        )

    def occupied_positions(self, position_min: int, position_max: int) -> set[tuple[int, int, int]]:
        """The (galaxy, system, position) triples already taken in the given
        position range, so the service can offer only free ones (docs/adr/0118)."""
        rows = self._session.execute(
            select(PlanetRow.galaxy, PlanetRow.system, PlanetRow.position).where(
                PlanetRow.position.between(position_min, position_max)
            )
        )
        result: set[tuple[int, int, int]] = set()
        for galaxy, system, position in rows:
            assert galaxy is not None
            assert system is not None
            assert position is not None
            result.add((galaxy, system, position))
        return result

    def try_create_home_planet(
        self, user_id: UUID, galaxy: int, system: int, position: int
    ) -> UUID | None:
        """Try to insert "Homeworld" and its vault at the given coordinates.

        Returns the new planet ID, or None if the user already has a home
        planet (the partial unique index of docs/adr/0109 absorbs that race
        silently) or the coordinates are already taken
        (uq_planets_coordinates, docs/adr/0118). The caller tells the two
        apart with home_planet_exists, and tries another position in the
        second case. The caller commits or rolls back.
        """
        statement = (
            insert(PlanetRow)
            .values(
                id=uuid4(),
                user_id=user_id,
                name=HOME_PLANET_NAME,
                is_home=True,
                galaxy=galaxy,
                system=system,
                position=position,
            )
            .on_conflict_do_nothing(index_elements=["user_id"], index_where=text("is_home"))
            .returning(PlanetRow.id)
        )
        try:
            with self._session.begin_nested():
                created_id = self._session.scalars(statement).one_or_none()
        except IntegrityError:
            return None
        if created_id is not None:
            self._session.add(
                VaultRow(
                    planet_id=created_id,
                    metal=START_METAL,
                    crystal=START_CRYSTAL,
                    deuterium=START_DEUTERIUM,
                )
            )
        return created_id

    def planets_in_system(self, galaxy: int, system: int) -> dict[int, tuple[str, str]]:
        """{position: (planet name, owner username)} for the occupied positions
        of one system. A join on UserRow, so the galaxy view needs no change
        to auth/public_api.py (docs/adr/0118)."""
        rows = self._session.execute(
            select(PlanetRow.position, PlanetRow.name, UserRow.username)
            .join(UserRow, UserRow.id == PlanetRow.user_id)
            .where(PlanetRow.galaxy == galaxy, PlanetRow.system == system)
        )
        result: dict[int, tuple[str, str]] = {}
        for position, name, username in rows:
            assert position is not None
            assert username is not None
            result[position] = (name, username)
        return result

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

    def list_planet_ids_for_user(self, user_id: UUID) -> list[UUID]:
        """Planet IDs of the user, in order, so a caller can lock their vaults
        in that order and so prevent a deadlock (docs/adr/0117)."""
        return list(
            self._session.scalars(
                select(PlanetRow.id).where(PlanetRow.user_id == user_id).order_by(PlanetRow.id)
            )
        )

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

    def get_ship_counts(self, planet_id: UUID) -> dict[str, int]:
        # populate_existing: after the vault lock, read what the other request committed.
        rows = self._session.scalars(
            select(ShipRow)
            .where(ShipRow.planet_id == planet_id)
            .execution_options(populate_existing=True)
        )
        return {row.kind: row.count for row in rows}

    def add_ships(self, planet_id: UUID, kind: ShipKind, number: int) -> None:
        statement = insert(ShipRow).values(planet_id=planet_id, kind=kind, count=number)
        self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["planet_id", "kind"],
                set_={"count": ShipRow.count + number},
            )
        )

    def get_ship_order(self, planet_id: UUID) -> StoredShipOrder | None:
        # populate_existing: after the vault lock, read what the other request committed.
        row = self._session.scalars(
            select(ShipOrderRow)
            .where(ShipOrderRow.planet_id == planet_id)
            .execution_options(populate_existing=True)
        ).one_or_none()
        if row is None:
            return None
        return StoredShipOrder(
            kind=_to_ship_kind(row.kind),
            remaining=row.remaining,
            seconds_per_ship=row.seconds_per_ship,
            next_finishes_at=row.next_finishes_at,
        )

    def add_ship_order(
        self,
        planet_id: UUID,
        kind: ShipKind,
        remaining: int,
        seconds_per_ship: int,
        next_finishes_at: datetime,
    ) -> None:
        self._session.add(
            ShipOrderRow(
                planet_id=planet_id,
                kind=kind,
                remaining=remaining,
                seconds_per_ship=seconds_per_ship,
                next_finishes_at=next_finishes_at,
            )
        )
        self._session.flush()

    def update_ship_order(
        self, planet_id: UUID, remaining: int, next_finishes_at: datetime
    ) -> None:
        self._session.execute(
            update(ShipOrderRow)
            .where(ShipOrderRow.planet_id == planet_id)
            .values(remaining=remaining, next_finishes_at=next_finishes_at)
        )

    def delete_ship_order(self, planet_id: UUID) -> None:
        self._session.execute(delete(ShipOrderRow).where(ShipOrderRow.planet_id == planet_id))

    def get_technology_levels(self, user_id: UUID) -> dict[str, int]:
        rows = self._session.scalars(
            select(TechnologyRow).where(TechnologyRow.user_id == user_id)
        )
        return {row.kind: row.level for row in rows}

    def set_technology_level(self, user_id: UUID, kind: str, level: int) -> None:
        statement = (
            insert(TechnologyRow)
            .values(user_id=user_id, kind=kind, level=level)
            .on_conflict_do_update(
                index_elements=["user_id", "kind"],
                set_={"level": level},
            )
        )
        self._session.execute(statement)

    def get_research(self, user_id: UUID) -> StoredResearch | None:
        # populate_existing: after the vault locks, read what another request committed.
        row = self._session.scalars(
            select(ResearchRow)
            .where(ResearchRow.user_id == user_id)
            .execution_options(populate_existing=True)
        ).one_or_none()
        if row is None:
            return None
        return StoredResearch(
            kind=_to_tech_kind(row.kind), planet_id=row.planet_id, finishes_at=row.finishes_at
        )

    def add_research(
        self, user_id: UUID, kind: TechKind, planet_id: UUID, finishes_at: datetime
    ) -> None:
        self._session.add(
            ResearchRow(user_id=user_id, kind=kind, planet_id=planet_id, finishes_at=finishes_at)
        )
        self._session.flush()

    def delete_research(self, user_id: UUID) -> None:
        self._session.execute(delete(ResearchRow).where(ResearchRow.user_id == user_id))

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
