"""add coordinates and username

Revision ID: 8a411d6206f3
Revises: eea904393c9c
Create Date: 2026-11-23 07:24:53.480105
"""

from collections.abc import Sequence

import random

import sqlalchemy as sa
from alembic import op


revision: str = '8a411d6206f3'
down_revision: str | None = 'eea904393c9c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The defaults of the settings galaxies and systems_per_galaxy (docs/adr/0118).
_GALAXIES = 1
_SYSTEMS = 50
# A home planet goes to a random free position in this range.
_HOME_POSITIONS = range(4, 13)


def upgrade() -> None:
    # docs/adr/0118: coordinates for each planet, and a public username.
    # The columns stay nullable until the backend sets them for each new row.
    op.add_column('planets', sa.Column('galaxy', sa.Integer(), nullable=True))
    op.add_column('planets', sa.Column('system', sa.Integer(), nullable=True))
    op.add_column('planets', sa.Column('position', sa.Integer(), nullable=True))
    op.create_unique_constraint('uq_planets_coordinates', 'planets', ['galaxy', 'system', 'position'])
    op.create_check_constraint('galaxy_positive', 'planets', 'galaxy >= 1')
    op.create_check_constraint('system_positive', 'planets', 'system >= 1')
    op.create_check_constraint('position_in_system', 'planets', 'position BETWEEN 1 AND 15')
    op.add_column('users', sa.Column('username', sa.String(length=20), nullable=True))
    op.create_unique_constraint('users_username_key', 'users', ['username'])

    bind = op.get_bind()
    # Existing users get player-<number>, in the order of registration.
    bind.execute(sa.text(
        "UPDATE users SET username = 'player-' || numbered.n FROM ("
        " SELECT id, row_number() OVER (ORDER BY created_at, id) AS n FROM users"
        ") AS numbered WHERE users.id = numbered.id"
    ))
    # Existing planets get a random free position, by the rule for a new home planet.
    free = [
        (galaxy, system, position)
        for galaxy in range(1, _GALAXIES + 1)
        for system in range(1, _SYSTEMS + 1)
        for position in _HOME_POSITIONS
    ]
    random.shuffle(free)
    planet_ids = bind.execute(sa.text("SELECT id FROM planets ORDER BY created_at, id")).scalars()
    for planet_id in planet_ids:
        galaxy, system, position = free.pop()
        bind.execute(
            sa.text("UPDATE planets SET galaxy = :g, system = :s, position = :p WHERE id = :id"),
            {"g": galaxy, "s": system, "p": position, "id": planet_id},
        )


def downgrade() -> None:
    op.drop_constraint('users_username_key', 'users', type_='unique')
    op.drop_column('users', 'username')
    op.drop_constraint('position_in_system', 'planets', type_='check')
    op.drop_constraint('system_positive', 'planets', type_='check')
    op.drop_constraint('galaxy_positive', 'planets', type_='check')
    op.drop_constraint('uq_planets_coordinates', 'planets', type_='unique')
    op.drop_column('planets', 'position')
    op.drop_column('planets', 'system')
    op.drop_column('planets', 'galaxy')
