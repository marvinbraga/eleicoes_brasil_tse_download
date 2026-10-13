"""Guarda as grades do relatório de poder. A senha fica na fábrica de conexão."""

from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Final, TypeVar

import psycopg

from eleicoes.adapters.postgres_sink import ConnectionFactory, CursorWork, SqlConnection, SqlCursor
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.ports.relatorio_poder import StoredReport

_TABLES_SQL = (Path(__file__).resolve().parent / "sql" / "tables.sql").read_text(encoding="utf-8")
_WIDTH: Final = 8
_CLOCK: Final = 7
_HEADER = (
    "INSERT INTO analise.relatorio_poder (ano, turno, cargo) "
    "VALUES (%s, %s, %s) "
    "ON CONFLICT (ano, turno, cargo) DO UPDATE "
    "SET gerado_em = now() "
    "RETURNING gerado_em"
)
_DELETE = "DELETE FROM analise.relatorio_poder_linha WHERE ano = %s AND turno = %s AND cargo = %s"
_INSERT = (
    "INSERT INTO analise.relatorio_poder_linha ("
    "ano, turno, cargo, nivel, codigo, nome, comparecimento, "
    "partido, votos_nominais, votos_legenda) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
_LOAD = (
    "SELECT linha.nivel, linha.codigo, linha.nome, linha.comparecimento, "
    "linha.partido, linha.votos_nominais, linha.votos_legenda, "
    "cabecalho.gerado_em "
    "FROM analise.relatorio_poder AS cabecalho "
    "LEFT JOIN analise.relatorio_poder_linha AS linha "
    "ON linha.ano = cabecalho.ano AND linha.turno = cabecalho.turno "
    "AND linha.cargo = cabecalho.cargo "
    "WHERE cabecalho.ano = %s AND cabecalho.turno = %s AND cabecalho.cargo = %s"
)
_T = TypeVar("_T")


class PostgresPowerReportStore:
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect
        self._connection: SqlConnection | None = None

    def ensure_model(self) -> None:
        self._run(lambda cursor: _execute_script(cursor, _TABLES_SQL))

    def load(self, ano: int, turno: int, cargo: str) -> StoredReport | None:
        return self._guard(lambda: self._load(ano, turno, cargo))

    def save(
        self,
        ano: int,
        turno: int,
        cargo: str,
        cells: tuple[StoredCell, ...],
    ) -> datetime:
        return self._guard(lambda: self._save(ano, turno, cargo, cells))

    def close(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            connection.close()

    def _load(self, ano: int, turno: int, cargo: str) -> StoredReport | None:
        self.ensure_model()
        found: list[StoredReport | None] = [None]

        def work(cursor: SqlCursor) -> None:
            found[0] = _read(cursor, ano, turno, cargo)

        self._run(work)
        return found[0]

    def _save(
        self,
        ano: int,
        turno: int,
        cargo: str,
        cells: tuple[StoredCell, ...],
    ) -> datetime:
        self.ensure_model()
        found: list[datetime] = []

        def work(cursor: SqlCursor) -> None:
            found.append(_write(cursor, ano, turno, cargo, cells))

        self._run(work)
        return found[0]

    def _guard(self, work: Callable[[], _T]) -> _T:
        try:
            return work()
        except ElectionError:
            raise
        except psycopg.Error as exc:
            raise ElectionError("power report store failed") from exc

    def _run(self, work: CursorWork) -> None:
        connection = self._open()
        with connection.transaction(), connection.cursor() as cursor:
            work(cursor)

    def _open(self) -> SqlConnection:
        if self._connection is None:
            self._connection = self._connect()
        return self._connection


def _read(cursor: SqlCursor, ano: int, turno: int, cargo: str) -> StoredReport | None:
    cursor.execute(_LOAD, (ano, turno, cargo))
    rows = tuple(tuple(row) for row in cursor.fetchall())
    if not rows:
        return None
    return StoredReport(_cells(rows), _clocks(rows))


def _cells(rows: tuple[tuple[object, ...], ...]) -> tuple[StoredCell, ...]:
    found: list[StoredCell] = []
    for row in rows:
        cell = _cell(row)
        if cell is not None:
            found.append(cell)
    return tuple(found)


def _cell(row: tuple[object, ...]) -> StoredCell | None:
    _width(row)
    if _absent(row):
        return None
    return StoredCell(
        _text(row[0]),
        _text(row[1]),
        _text(row[2]),
        _count(row[3]),
        _count(row[4]),
        _count(row[5]),
        _count(row[6]),
    )


def _write(
    cursor: SqlCursor,
    ano: int,
    turno: int,
    cargo: str,
    cells: tuple[StoredCell, ...],
) -> datetime:
    cursor.execute(_HEADER, (ano, turno, cargo))
    moment = _returned(cursor)
    cursor.execute(_DELETE, (ano, turno, cargo))
    _insert_lines(cursor, ano, turno, cargo, cells)
    return moment


def _insert_lines(
    cursor: SqlCursor,
    ano: int,
    turno: int,
    cargo: str,
    cells: tuple[StoredCell, ...],
) -> None:
    for cell in cells:
        cursor.execute(_INSERT, _line(ano, turno, cargo, cell))


def _line(ano: int, turno: int, cargo: str, cell: StoredCell) -> tuple[object, ...]:
    return (
        ano,
        turno,
        cargo,
        cell.nivel,
        cell.codigo,
        cell.nome,
        cell.comparecimento,
        cell.partido,
        cell.votos_nominais,
        cell.votos_legenda,
    )


def _returned(cursor: SqlCursor) -> datetime:
    rows = tuple(tuple(row) for row in cursor.fetchall())
    if len(rows) != 1:
        raise ElectionError("power report was not stored")
    return _single_clock(rows[0])


def _single_clock(row: tuple[object, ...]) -> datetime:
    if len(row) != 1:
        raise ElectionError("power report was not stored")
    return _clock(row[0])


def _clocks(rows: tuple[tuple[object, ...], ...]) -> datetime:
    found = {_moment(row) for row in rows}
    if len(found) != 1:
        raise ElectionError("power report row is incomplete")
    return next(iter(found))


def _moment(row: tuple[object, ...]) -> datetime:
    _width(row)
    return _clock(row[_CLOCK])


def _width(row: tuple[object, ...]) -> None:
    if len(row) != _WIDTH:
        raise ElectionError("power report row is incomplete")


def _absent(row: tuple[object, ...]) -> bool:
    return all(item is None for item in row[:_CLOCK])


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ElectionError("power report row is incomplete")
    return value


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ElectionError("power report row is incomplete")
    return value


def _clock(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise ElectionError("power report row is incomplete")
    return value


def _execute_script(cursor: SqlCursor, script: str) -> None:
    for statement in _statements(script):
        cursor.execute(statement)


def _statements(script: str) -> Iterator[str]:
    for chunk in script.split(";"):
        statement = chunk.strip()
        if statement:
            yield statement
