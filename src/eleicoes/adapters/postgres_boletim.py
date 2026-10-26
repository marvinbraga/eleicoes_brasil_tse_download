"""Grava boletins no Postgres. Uma transação substitui só a UF pedida."""

from collections.abc import Sequence
from typing import Final, Protocol

from eleicoes.adapters.postgres_sink import (
    ConnectionFactory,
    CursorWork,
    SqlConnection,
    SqlCursor,
    require_current_revision,
)
from eleicoes.domain.boletim import Boletim, VoteLine
from eleicoes.domain.values import ElectionYear, Turno, Uf

_COLUMNS: Final[tuple[str, ...]] = (
    "ano",
    "turno",
    "uf",
    "municipio",
    "zona",
    "secao",
    "local",
    "arquivo",
    "id_eleicao",
    "eleitores_aptos",
    "qtd_comparecimento",
    "eleitores_complemento",
    "eleitores_computados",
    "indicador_habilitacao",
    "qtd_biometria",
    "qtd_manual",
    "tipo_cargo",
    "cargo",
    "ordem_impressao",
    "comparecimento_cargo",
    "tipo_voto",
    "partido",
    "numero",
    "quantidade",
    "numero_interno_urna",
    "codigo_carga",
    "codigo_midia",
    "data_hora_emissao",
    "data_hora_carga",
)
_COPY: Final = "COPY raw.boletim (" + ", ".join(_COLUMNS) + ") FROM STDIN"
_DELETE: Final = "DELETE FROM raw.boletim WHERE ano = %s AND turno = %s AND uf = %s"
# Cada carga da UF deixa uma marca em raw.carga, na mesma transação. clock_timestamp() é o
# instante depois do COPY: now() seria o início da transação e perderia uma carga longa.
_FORGET_LOAD: Final = "DELETE FROM raw.carga WHERE arquivo = %s AND membro = %s"
_RECORD_LOAD: Final = (
    "INSERT INTO raw.carga "
    "(conjunto, turno, uf, arquivo, membro, tabela, geracao, linhas, situacao, carregado_em) "
    "VALUES (%s, %s, %s, %s, %s, %s, '', %s, 'carregado', clock_timestamp())"
)
LOAD_TABLE: Final = "raw.boletim"
_LOAD_MEMBER: Final = "bu.dat"
BoletimCell = int | str | None
BoletimRow = tuple[BoletimCell, ...]


class PostgresBoletimSink:
    def __init__(self, connect: ConnectionFactory, schema: CursorWork | None = None) -> None:
        self._connect = connect
        self._schema = schema if schema is not None else require_current_revision
        self._connection: SqlConnection | None = None

    def ensure_model(self) -> None:
        self._run(self._schema)

    def replace_uf(
        self,
        year: ElectionYear,
        turno: Turno,
        uf: Uf,
        boletins: Sequence[Boletim],
    ) -> int:
        rows = _rows(year, turno, uf, boletins)
        scope = (year.value, turno.value, uf.code)

        def work(cursor: SqlCursor) -> None:
            _replace(cursor, scope, rows)

        self._run(work)
        return len(rows)

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _run(self, work: "_CursorWork") -> None:
        connection = self._open()
        with connection.transaction(), connection.cursor() as cursor:
            work(cursor)

    def _open(self) -> SqlConnection:
        if self._connection is None:
            self._connection = self._connect()
        return self._connection


class _CursorWork(Protocol):
    def __call__(self, cursor: SqlCursor) -> None: ...


def _replace(cursor: SqlCursor, scope: tuple[int, int, str], rows: Sequence[BoletimRow]) -> None:
    cursor.execute(_DELETE, scope)
    if rows:
        with cursor.copy(_COPY) as stream:
            stream.write(_payload(rows))
    _record_load(cursor, scope, len(rows))


def load_set(ano: int) -> str:
    """raw.carga não tem coluna de ano: ele vai no conjunto."""
    return f"boletins-{ano}"


def _record_load(cursor: SqlCursor, scope: tuple[int, int, str], linhas: int) -> None:
    ano, turno, uf = scope
    arquivo = f"boletins/{ano}/turno-{turno}/{uf}"
    cursor.execute(_FORGET_LOAD, (arquivo, _LOAD_MEMBER))
    cursor.execute(
        _RECORD_LOAD,
        (load_set(ano), str(turno), uf, arquivo, _LOAD_MEMBER, LOAD_TABLE, linhas),
    )


def _rows(
    year: ElectionYear,
    turno: Turno,
    uf: Uf,
    boletins: Sequence[Boletim],
) -> tuple[BoletimRow, ...]:
    return tuple(
        _row(year, turno, uf, boletim, line) for boletim in boletins for line in boletim.votos
    )


def _row(
    year: ElectionYear,
    turno: Turno,
    uf: Uf,
    boletim: Boletim,
    line: VoteLine,
) -> BoletimRow:
    return (
        year.value,
        turno.value,
        uf.code,
        boletim.municipio,
        boletim.zona,
        boletim.secao,
        boletim.local,
        boletim.arquivo,
        line.id_eleicao,
        line.eleitores_aptos,
        line.qtd_comparecimento,
        line.qtd_eleitores_complemento,
        boletim.eleitores_computados,
        boletim.indicador_habilitacao,
        boletim.qtd_biometria,
        boletim.qtd_manual,
        line.tipo_cargo,
        line.cargo,
        line.ordem_impressao,
        line.comparecimento_cargo,
        line.tipo_voto,
        line.partido,
        line.numero,
        line.quantidade,
        boletim.numero_interno_urna,
        boletim.codigo_carga,
        boletim.codigo_midia,
        boletim.data_hora_emissao,
        boletim.data_hora_carga,
    )


def _payload(rows: Sequence[BoletimRow]) -> bytes:
    return b"".join(_line(row) for row in rows)


def _line(row: BoletimRow) -> bytes:
    return ("\t".join(_field(value) for value in row) + "\n").encode("utf-8")


def _field(value: BoletimCell) -> str:
    if value is None:
        return r"\N"
    if isinstance(value, str):
        return _escape(value)
    return str(value)


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    )
