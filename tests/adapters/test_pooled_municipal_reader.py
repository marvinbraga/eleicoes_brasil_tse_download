"""The scoreboard's 2024 reader borrows a pooled connection only while it reads."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

from eleicoes.adapters import postgres_municipais_async as module
from eleicoes.adapters.postgres_municipais_async import PooledMunicipalReader
from eleicoes.ports.async_sql import AsyncSqlConnection


class _Pool:
    def __init__(self) -> None:
        self.borrowed = 0
        self.open = 0

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[AsyncSqlConnection]:
        self.borrowed += 1
        self.open += 1
        try:
            yield object()  # type: ignore[misc]
        finally:
            self.open -= 1


class _Reader:
    calls: list[tuple[str, object]] = []

    def __init__(self, connection: object) -> None:
        self.connection = connection

    async def load(self, ano: int, uf: str | None) -> None:
        _Reader.calls.append(("load", (ano, uf)))

    async def party_counts_by_uf(self, ano: int) -> None:
        _Reader.calls.append(("counts", ano))


def test_each_read_borrows_and_returns_one_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "AsyncPostgresMunicipalReader", _Reader)
    _Reader.calls = []
    pool = _Pool()
    reader = PooledMunicipalReader(pool)  # type: ignore[arg-type]
    assert pool.borrowed == 0
    asyncio.run(reader.party_counts_by_uf(2024))
    asyncio.run(reader.load(2024, "AC"))
    assert pool.borrowed == 2
    assert pool.open == 0
    assert _Reader.calls == [("counts", 2024), ("load", (2024, "AC"))]
