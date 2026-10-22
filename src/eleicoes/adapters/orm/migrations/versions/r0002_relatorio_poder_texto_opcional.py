"""Relax the legacy html and resumo columns of analise.relatorio_poder, only where they exist.

Revision ID: 0002
Revises: 0001
"""

from typing import Final

from alembic import op

revision: Final = "0002"
down_revision: Final[str | None] = "0001"
branch_labels: Final[str | None] = None
depends_on: Final[str | None] = None

_LEGACY_COLUMNS: Final = ("html", "resumo")
_RELAX: Final = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'analise'
            AND table_name = 'relatorio_poder'
            AND column_name = '{column}'
    ) THEN
        ALTER TABLE analise.relatorio_poder ALTER COLUMN {column} DROP NOT NULL;
    END IF;
END
$$
"""


def upgrade() -> None:
    for column in _LEGACY_COLUMNS:
        op.execute(_RELAX.format(column=column))


def downgrade() -> None:
    """Restoring NOT NULL would reject the rows the current code writes without text."""
