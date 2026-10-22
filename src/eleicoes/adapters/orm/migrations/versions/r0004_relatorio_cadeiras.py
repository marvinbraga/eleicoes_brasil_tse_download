"""Votes per candidate number for the seat estimate: analise.relatorio_cadeiras(_voto).

Revision ID: 0004
Revises: 0003
"""

from typing import Final

from alembic import op

revision: Final = "0004"
down_revision: Final[str | None] = "0003"
branch_labels: Final[str | None] = None
depends_on: Final[str | None] = None

_DDL: Final = (
    """
CREATE TABLE IF NOT EXISTS analise.relatorio_cadeiras (
    ano integer NOT NULL,
    turno integer NOT NULL,
    cargo text NOT NULL,
    gerado_em timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ano, turno, cargo)
)
""",
    """
CREATE TABLE IF NOT EXISTS analise.relatorio_cadeiras_voto (
    ano integer NOT NULL,
    turno integer NOT NULL,
    cargo text NOT NULL,
    uf text NOT NULL,
    tipo_voto text NOT NULL CHECK (tipo_voto IN ('nominal', 'legenda')),
    numero integer NOT NULL CHECK (numero >= 0),
    votos integer NOT NULL CHECK (votos >= 0),
    PRIMARY KEY (ano, turno, cargo, uf, tipo_voto, numero),
    FOREIGN KEY (ano, turno, cargo)
        REFERENCES analise.relatorio_cadeiras (ano, turno, cargo) ON DELETE CASCADE
)
""",
)


def upgrade() -> None:
    for statement in _DDL:
        op.execute(statement.strip())


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS analise.relatorio_cadeiras_voto")
    op.execute("DROP TABLE IF EXISTS analise.relatorio_cadeiras")
