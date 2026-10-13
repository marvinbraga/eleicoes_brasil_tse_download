"""One pooled connection is shared by every reader on the request."""

import asyncio

import httpx
from fastapi import FastAPI
from starlette.requests import Request
from tests.adapters.test_async_read_sql import _Connection, _Script

from eleicoes.adapters.http.dependencies import (
    get_boletim_reader,
    get_connection,
    get_cross_store,
    get_municipality_names,
    get_power_store,
)
from eleicoes.adapters.postgres_boletim_consulta_async import AsyncPostgresBoletimReader
from eleicoes.adapters.postgres_municipio_async import AsyncPostgresMunicipalityNames
from eleicoes.adapters.postgres_relatorio_poder_async import AsyncPostgresPowerReportStore
from eleicoes.adapters.postgres_relatorio_presidente_governador_async import (
    AsyncPostgresPresidentGovernorStore,
)
from eleicoes.composition.api import create_app


class _Checkout:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection
        self.entered = 0

    async def __aenter__(self) -> _Connection:
        self.entered += 1
        return self.connection

    async def __aexit__(self, *_args: object) -> None:
        return None


class _Pool:
    def __init__(self, connection: _Connection) -> None:
        self.checkout = _Checkout(connection)

    def connection(self) -> _Checkout:
        return self.checkout


def test_providers_build_postgres_adapters_from_one_connection() -> None:
    script = _Script()
    pool = _Pool(_Connection(script))
    application = create_app()
    application.state.pool = pool
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "app": application,
    }
    request = Request(scope)

    async def resolve() -> tuple[object, ...]:
        generator = get_connection(request)
        connection = await anext(generator)
        found = (
            await get_boletim_reader(request, connection),
            await get_municipality_names(request, connection),
            await get_power_store(request, connection),
            await get_cross_store(request, connection),
        )
        await generator.aclose()
        return found

    reader, names, power, cross = asyncio.run(resolve())
    assert isinstance(reader, AsyncPostgresBoletimReader)
    assert isinstance(names, AsyncPostgresMunicipalityNames)
    assert isinstance(power, AsyncPostgresPowerReportStore)
    assert isinstance(cross, AsyncPostgresPresidentGovernorStore)
    assert pool.checkout.entered == 1


def test_voting_route_checks_out_one_connection() -> None:
    script = _Script()
    script.push(("nominal", 13, 13, 8))
    pool = _Pool(_Connection(script))
    application = create_app()
    application.state.pool = pool
    path = "/votos/cargos?ano=2026&turno=1&uf=SE&cargo=presidente"
    response = asyncio.run(_get(application, path))
    assert response.status_code == 200
    assert response.json() == [
        {"tipo_voto": "nominal", "partido": 13, "numero": 13, "quantidade": 8}
    ]
    assert pool.checkout.entered == 1


async def _get(application: FastAPI, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)
