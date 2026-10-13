"""Runs one read transaction. SQL text stays in the synchronous adapters."""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

import psycopg

from eleicoes.domain.errors import ElectionError
from eleicoes.ports.async_sql import AsyncSqlConnection, AsyncSqlCursor


@asynccontextmanager
async def query_cursor(connection: AsyncSqlConnection) -> AsyncIterator[AsyncSqlCursor]:
    try:
        async with connection.transaction(), connection.cursor() as cursor:
            yield cursor
    except psycopg.Error as exc:
        raise ElectionError("database read failed") from exc


async def fetch_all(
    connection: AsyncSqlConnection,
    sql: str,
    params: Sequence[object],
) -> tuple[tuple[object, ...], ...]:
    async with query_cursor(connection) as cursor:
        await cursor.execute(sql, params)
        fetched = await cursor.fetchall()
    return tuple(tuple(row) for row in fetched)
