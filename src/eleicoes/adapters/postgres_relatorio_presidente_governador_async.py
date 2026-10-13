"""Async cache of president × governor places. Same statements as the sync store."""

from collections.abc import Sequence
from datetime import datetime

from eleicoes.adapters.async_query import query_cursor
from eleicoes.adapters.postgres_relatorio_presidente_governador import (
    _DELETE_CEDULA,
    _DELETE_LINHA,
    _GOVERNOR,
    _HEADER,
    _INSERT_CEDULA,
    _INSERT_LINHA,
    _LOAD_CEDULA,
    _LOAD_HEADER,
    _LOAD_LINHA,
    _PRESIDENT,
    _cedula_params,
    _line,
    _one_clock,
    _places,
)
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace
from eleicoes.ports.async_sql import AsyncSqlConnection, AsyncSqlCursor
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport


class AsyncPostgresPresidentGovernorStore:
    def __init__(self, connection: AsyncSqlConnection) -> None:
        self._connection = connection

    async def load(self, ano: int, turno: int) -> StoredCrossReport | None:
        async with query_cursor(self._connection) as cursor:
            header = await _fetch(cursor, _LOAD_HEADER, (ano, turno))
            if not header:
                return None
            lines = await _fetch(cursor, _LOAD_LINHA, (ano, turno))
            cedulas = await _fetch(cursor, _LOAD_CEDULA, (ano, turno))
        return StoredCrossReport(_places(lines, cedulas), _one_clock(header))

    async def save(
        self,
        ano: int,
        turno: int,
        places: tuple[MunicipalPlace, ...],
    ) -> datetime:
        async with query_cursor(self._connection) as cursor:
            await cursor.execute(_HEADER, (ano, turno))
            header = await _fetched(cursor)
            await cursor.execute(_DELETE_LINHA, (ano, turno))
            await cursor.execute(_DELETE_CEDULA, (ano, turno))
            for place in places:
                await _insert_place(cursor, ano, turno, place)
        return _one_clock(header)


async def _insert_place(
    cursor: AsyncSqlCursor,
    ano: int,
    turno: int,
    place: MunicipalPlace,
) -> None:
    await _insert_cargo(cursor, ano, turno, place, _PRESIDENT, place.presidente)
    if place.governador is not None:
        await _insert_cargo(cursor, ano, turno, place, _GOVERNOR, place.governador)


async def _insert_cargo(
    cursor: AsyncSqlCursor,
    ano: int,
    turno: int,
    place: MunicipalPlace,
    cargo: str,
    tally: CargoTally,
) -> None:
    for party in tally.parties:
        await cursor.execute(_INSERT_LINHA, _line(ano, turno, place, cargo, party))
    await cursor.execute(_INSERT_CEDULA, _cedula_params(ano, turno, place, cargo, tally))


async def _fetch(
    cursor: AsyncSqlCursor,
    sql: str,
    params: tuple[object, ...],
) -> tuple[tuple[object, ...], ...]:
    await cursor.execute(sql, params)
    return await _fetched(cursor)


async def _fetched(cursor: AsyncSqlCursor) -> tuple[tuple[object, ...], ...]:
    return _as_tuples(await cursor.fetchall())


def _as_tuples(rows: Sequence[Sequence[object]]) -> tuple[tuple[object, ...], ...]:
    return tuple(tuple(row) for row in rows)
