"""Municipal results: raw CSV tables of consulta_cand, consulta_vagas, detalhe_votacao_munzona
and the analise tables rebuilt by import-municipais.

Revision ID: 0005
Revises: 0004
"""

from typing import Final

from alembic import op

from eleicoes.domain.municipal_contract import (
    CONSULTA_CAND,
    CONSULTA_VAGAS,
    DETALHE_VOTACAO_MUNZONA,
)
from eleicoes.domain.tabular_contract import TabularContract

revision: Final = "0005"
down_revision: Final[str | None] = "0004"
branch_labels: Final[str | None] = None
depends_on: Final[str | None] = None

_RAW: Final = (CONSULTA_CAND, CONSULTA_VAGAS, DETALHE_VOTACAO_MUNZONA)
_ANALISE: Final = """
CREATE TABLE IF NOT EXISTS analise.municipal_carga (
    ano integer PRIMARY KEY,
    geracao text NOT NULL,
    municipios integer NOT NULL,
    prefeitos integer NOT NULL,
    vereadores integer NOT NULL,
    divergencias_vagas integer NOT NULL,
    gerado_em timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analise.municipal_prefeito (
    ano integer NOT NULL,
    sg_uf text NOT NULL,
    cd_municipio_tse text NOT NULL,
    nm_municipio text NOT NULL,
    eleitorado bigint NOT NULL,
    vagas_vereador integer NOT NULL,
    nr_partido integer,
    sg_partido text,
    nm_urna text,
    sq_candidato text,
    dt_eleicao date,
    nr_turno integer,
    suplementar boolean NOT NULL DEFAULT false,
    PRIMARY KEY (ano, sg_uf, cd_municipio_tse),
    FOREIGN KEY (ano) REFERENCES analise.municipal_carga (ano) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS municipal_prefeito_partido_idx
    ON analise.municipal_prefeito (ano, nr_partido);

CREATE TABLE IF NOT EXISTS analise.municipal_vereador (
    ano integer NOT NULL,
    sg_uf text NOT NULL,
    cd_municipio_tse text NOT NULL,
    nr_partido integer NOT NULL,
    sg_partido text NOT NULL,
    eleitos integer NOT NULL,
    PRIMARY KEY (ano, sg_uf, cd_municipio_tse, nr_partido),
    FOREIGN KEY (ano) REFERENCES analise.municipal_carga (ano) ON DELETE CASCADE
)
"""


def _raw_ddl(contract: TabularContract) -> tuple[str, ...]:
    columns = ",\n    ".join(f"{name.lower()} text" for name in contract.columns)
    table = contract.table
    return (
        f"CREATE TABLE IF NOT EXISTS raw.{table} (\n    {columns},\n"
        "    arquivo text NOT NULL,\n    membro text NOT NULL,\n    geracao text NOT NULL\n)",
        f"CREATE INDEX IF NOT EXISTS {table}_arquivo_membro_idx ON raw.{table} (arquivo, membro)",
        f"CREATE INDEX IF NOT EXISTS {table}_ano_cargo_idx ON raw.{table} (ano_eleicao, cd_cargo)",
    )


def upgrade() -> None:
    for contract in _RAW:
        for statement in _raw_ddl(contract):
            op.execute(statement)
    for chunk in _ANALISE.split(";"):
        statement = chunk.strip()
        if statement:
            op.execute(statement)


def downgrade() -> None:
    for table in (
        "analise.municipal_vereador",
        "analise.municipal_prefeito",
        "analise.municipal_carga",
        "raw.detalhe_votacao_munzona",
        "raw.consulta_vagas",
        "raw.consulta_cand",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
