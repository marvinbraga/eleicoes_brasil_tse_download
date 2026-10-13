"""Async cache of party-power cells. Same statements as the sync store, without DDL."""

from collections.abc import Sequence
from datetime import datetime

from eleicoes.adapters.async_query import fetch_all, query_cursor
from eleicoes.adapters.postgres_relatorio_poder import (
    _DELETE,
    _HEADER,
    _INSERT,
    _LOAD,
    _cells,
    _clocks,
    _line,
    _single_clock,
)
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.ports.async_sql import AsyncSqlConnection, AsyncSqlCursor
from eleicoes.ports.relatorio_poder import StoredReport


class AsyncPostgresPowerReportStore:
    def __init__(self, connection: AsyncSqlConnection) -> None:
        self._connection = connection

    async def load(self, ano: int, turno: int, cargo: str) -> StoredReport | None:
        rows = await fetch_all(self._connection, _LOAD, (ano, turno, cargo))
        if not rows:
            return None
        return StoredReport(_cells(rows), _clocks(rows))

    async def save(
        self,
        ano: int,
        turno: int,
        cargo: str,
        cells: tuple[StoredCell, ...],
    ) -> datetime:
        async with query_cursor(self._connection) as cursor:
            await cursor.execute(_HEADER, (ano, turno, cargo))
            moment = _stored_clock(await cursor.fetchall())
            await cursor.execute(_DELETE, (ano, turno, cargo))
            await _insert_lines(cursor, ano, turno, cargo, cells)
        return moment


async def _insert_lines(
    cursor: AsyncSqlCursor,
    ano: int,
    turno: int,
    cargo: str,
    cells: tuple[StoredCell, ...],
) -> None:
    for cell in cells:
        await cursor.execute(_INSERT, _line(ano, turno, cargo, cell))


def _stored_clock(rows: Sequence[Sequence[object]]) -> datetime:
    parsed = tuple(tuple(row) for row in rows)
    if len(parsed) != 1:
        raise ElectionError("power report was not stored")
    return _single_clock(parsed[0])
