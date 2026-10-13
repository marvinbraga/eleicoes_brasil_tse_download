"""Async municipality names. Same query as PostgresMunicipalityNames."""

from collections.abc import Mapping

from eleicoes.adapters.async_query import fetch_all
from eleicoes.adapters.postgres_municipio import _NAMES, _names
from eleicoes.domain.values import Uf
from eleicoes.ports.async_sql import AsyncSqlConnection


class AsyncPostgresMunicipalityNames:
    def __init__(self, connection: AsyncSqlConnection) -> None:
        self._connection = connection

    async def names(self, uf: str) -> Mapping[int, str]:
        rows = await fetch_all(self._connection, _NAMES, (Uf(uf).code,))
        return _names(rows)
