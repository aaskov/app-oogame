"""allow storage

Revision ID: 6e9c2b999916
Revises: eee81d317ac4
Create Date: 2026-10-23 07:26:39.031608
"""

from collections.abc import Sequence

from alembic import op


revision: str = '6e9c2b999916'
down_revision: str | None = 'eee81d317ac4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OLD = "'metal_mine', 'crystal_mine', 'deuterium_synthesizer', 'solar_plant'"
_STORAGE = "'metal_storage', 'crystal_storage', 'deuterium_tank'"


def upgrade() -> None:
    # docs/adr/0113: three storage kinds.
    op.drop_constraint("known_kind", "buildings", type_="check")
    op.create_check_constraint("known_kind", "buildings", f"kind IN ({_OLD}, {_STORAGE})")


def downgrade() -> None:
    # The old constraint does not allow storage, so its rows go first.
    op.execute(f"DELETE FROM buildings WHERE kind IN ({_STORAGE})")
    op.drop_constraint("known_kind", "buildings", type_="check")
    op.create_check_constraint("known_kind", "buildings", f"kind IN ({_OLD})")
