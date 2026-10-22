"""allow solar plant

Revision ID: eee81d317ac4
Revises: 1c6ec99a1fdb
Create Date: 2026-10-22 17:57:41.435036
"""

from collections.abc import Sequence

from alembic import op


revision: str = 'eee81d317ac4'
down_revision: str | None = '1c6ec99a1fdb'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_MINES = "'metal_mine', 'crystal_mine', 'deuterium_synthesizer'"


def upgrade() -> None:
    # docs/adr/0112: the solar plant is a building kind.
    op.drop_constraint("known_kind", "buildings", type_="check")
    op.create_check_constraint("known_kind", "buildings", f"kind IN ({_MINES}, 'solar_plant')")


def downgrade() -> None:
    # The old constraint does not allow a solar plant, so its rows go first.
    op.execute("DELETE FROM buildings WHERE kind = 'solar_plant'")
    op.drop_constraint("known_kind", "buildings", type_="check")
    op.create_check_constraint("known_kind", "buildings", f"kind IN ({_MINES})")
