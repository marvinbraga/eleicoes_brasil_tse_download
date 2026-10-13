"""One pooled connection per request. Injected ports skip Postgres entirely."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request

from eleicoes.adapters.http.bundle import ReadPorts
from eleicoes.adapters.postgres_boletim_consulta_async import AsyncPostgresBoletimReader
from eleicoes.adapters.postgres_municipio_async import AsyncPostgresMunicipalityNames
from eleicoes.adapters.postgres_relatorio_poder_async import AsyncPostgresPowerReportStore
from eleicoes.adapters.postgres_relatorio_presidente_governador_async import (
    AsyncPostgresPresidentGovernorStore,
)
from eleicoes.domain.errors import ElectionError
from eleicoes.ports.async_sql import AsyncPool, AsyncSqlConnection
from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.ports.grade import AsyncMunicipalityNames
from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore
from eleicoes.ports.relatorio_presidente_governador import AsyncRelatorioPresidenteGovernadorStore


async def get_connection(request: Request) -> AsyncIterator[AsyncSqlConnection | None]:
    if _installed(request) is not None:
        yield None
        return
    async with _require_pool(request).connection() as connection:
        yield connection


Connection = Annotated[AsyncSqlConnection | None, Depends(get_connection)]


async def get_boletim_reader(request: Request, connection: Connection) -> AsyncBoletimReader:
    installed = _installed(request)
    if installed is not None:
        return installed.boletim
    return AsyncPostgresBoletimReader(cast(AsyncSqlConnection, connection))


async def get_municipality_names(
    request: Request,
    connection: Connection,
) -> AsyncMunicipalityNames:
    installed = _installed(request)
    if installed is not None:
        return installed.names
    return AsyncPostgresMunicipalityNames(cast(AsyncSqlConnection, connection))


async def get_power_store(request: Request, connection: Connection) -> AsyncRelatorioPoderStore:
    installed = _installed(request)
    if installed is not None:
        return installed.power_store
    return AsyncPostgresPowerReportStore(cast(AsyncSqlConnection, connection))


async def get_cross_store(
    request: Request,
    connection: Connection,
) -> AsyncRelatorioPresidenteGovernadorStore:
    installed = _installed(request)
    if installed is not None:
        return installed.cross_store
    return AsyncPostgresPresidentGovernorStore(cast(AsyncSqlConnection, connection))


def _installed(request: Request) -> ReadPorts | None:
    found = getattr(request.app.state, "ports", None)
    if isinstance(found, ReadPorts):
        return found
    return None


def _require_pool(request: Request) -> AsyncPool:
    found = getattr(request.app.state, "pool", None)
    if found is None:
        raise ElectionError("database pool is not configured")
    return cast(AsyncPool, found)
