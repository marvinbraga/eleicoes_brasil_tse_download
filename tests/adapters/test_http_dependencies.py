"""Boletim keeps the pool. Report stores share one async ORM session."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from tests.adapters.test_async_read_sql import _Connection, _Script

from eleicoes.adapters.http.bundle import ReadPorts
from eleicoes.adapters.http.dependencies import (
    get_boletim_reader,
    get_connection,
    get_cross_store,
    get_municipality_names,
    get_power_store,
    get_session,
)
from eleicoes.adapters.orm.sessions import AsyncSessionMaker
from eleicoes.adapters.postgres_boletim_consulta_async import AsyncPostgresBoletimReader
from eleicoes.adapters.postgres_municipio_async import AsyncPostgresMunicipalityNames
from eleicoes.adapters.postgres_relatorio_poder_async import AsyncPostgresPowerReportStore
from eleicoes.adapters.postgres_relatorio_presidente_governador_async import (
    AsyncPostgresPresidentGovernorStore,
)
from eleicoes.composition.api import create_app
from eleicoes.domain.errors import ElectionError


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


def test_boletim_uses_the_pool_and_reports_share_one_session() -> None:
    pool = _Pool(_Connection(_Script()))
    application = create_app()
    application.state.pool = pool
    maker = AsyncSessionMaker(_url())
    application.state.session_maker = maker
    request = _request(application)

    async def resolve() -> None:
        connections = get_connection(request)
        sessions = get_session(request)
        connection = await anext(connections)
        session = await anext(sessions)
        try:
            reader = await get_boletim_reader(request, connection)
            names = await get_municipality_names(request, session)
            power = await get_power_store(request, session)
            cross = await get_cross_store(request, session)
            assert isinstance(session, AsyncSession)
            assert isinstance(reader, AsyncPostgresBoletimReader)
            assert isinstance(names, AsyncPostgresMunicipalityNames)
            assert isinstance(power, AsyncPostgresPowerReportStore)
            assert isinstance(cross, AsyncPostgresPresidentGovernorStore)
        finally:
            await sessions.aclose()
            await connections.aclose()
            await maker.dispose()

    asyncio.run(resolve())
    assert pool.checkout.entered == 1


def test_installed_ports_do_not_open_a_session() -> None:
    sentinel = object()
    application = create_app(
        ports=ReadPorts(
            boletim=sentinel,
            names=sentinel,
            power_store=sentinel,
            cross_store=sentinel,
        )
    )
    request = _request(application)

    async def resolve() -> tuple[object, object]:
        sessions = get_session(request)
        found = await anext(sessions)
        await sessions.aclose()
        names = await get_municipality_names(request, None)
        return found, names

    found, names = asyncio.run(resolve())
    assert found is None
    assert names is sentinel


def test_missing_session_maker_is_an_election_error() -> None:
    application = create_app(pool_factory=lambda: _Pool(_Connection(_Script())))
    request = _request(application)

    async def open_session() -> None:
        sessions = get_session(request)
        await anext(sessions)

    with pytest.raises(ElectionError, match="database session is not configured"):
        asyncio.run(open_session())
    with pytest.raises(ElectionError, match="database session is not configured"):
        asyncio.run(get_power_store(request, None))


def _request(application: FastAPI) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "app": application,
    }
    return Request(scope)


def _url() -> URL:
    return URL.create(
        drivername="postgresql+psycopg",
        username="eleicoes",
        password="eleicoes",
        host="127.0.0.1",
        port=1,
        database="eleicoes",
    )


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
