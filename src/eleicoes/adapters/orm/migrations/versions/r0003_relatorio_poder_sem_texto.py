"""Drop the legacy html and resumo columns of analise.relatorio_poder. The text is gone for good.

Revision ID: 0003
Revises: 0002
"""

from typing import Final

from alembic import op

revision: Final = "0003"
down_revision: Final[str | None] = "0002"
branch_labels: Final[str | None] = None
depends_on: Final[str | None] = None

_LEGACY_COLUMNS: Final = ("html", "resumo")


def upgrade() -> None:
    for column in _LEGACY_COLUMNS:
        op.execute(f"ALTER TABLE analise.relatorio_poder DROP COLUMN IF EXISTS {column}")


def downgrade() -> None:
    """Brings the columns back as nullable and empty; the dropped text cannot be restored."""
    for column in _LEGACY_COLUMNS:
        op.execute(f"ALTER TABLE analise.relatorio_poder ADD COLUMN IF NOT EXISTS {column} text")
