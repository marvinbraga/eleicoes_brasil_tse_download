"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""

from typing import Final

from alembic import op
${imports if imports else ""}
revision: Final = ${repr(up_revision)}
down_revision: Final[str | None] = ${repr(down_revision)}
branch_labels: Final[str | None] = ${repr(branch_labels)}
depends_on: Final[str | None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Migrations here never drop columns or tables that hold imported data."""
