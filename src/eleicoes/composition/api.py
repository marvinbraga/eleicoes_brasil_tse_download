"""FastAPI factory. The pool and the async ORM engine open in the lifespan."""

import os
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from typing import cast

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from psycopg.conninfo import make_conninfo
from psycopg_pool import AsyncConnectionPool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ExceptionHandler

from eleicoes.adapters.health_api import health
from eleicoes.adapters.http.bundle import ReadPorts
from eleicoes.adapters.http.errors import (
    election_error,
    http_exception,
    invalid_request,
    unexpected,
)
from eleicoes.adapters.http.relatorios import router as relatorios_router
from eleicoes.adapters.http.verticalizacao import router as verticalizacao_router
from eleicoes.adapters.http.votos import router as votos_router
from eleicoes.adapters.orm.sessions import AsyncSessionMaker, database_endpoint, sqlalchemy_url
from eleicoes.composition.correspondencia import _host_settings
from eleicoes.domain.errors import ElectionError
from eleicoes.ports.async_sql import AsyncPool

PoolFactory = Callable[[], AsyncPool]
SessionMakerFactory = Callable[[], AsyncSessionMaker]


def create_app(
    ports: ReadPorts | None = None,
    pool_factory: PoolFactory | None = None,
    session_maker_factory: SessionMakerFactory | None = None,
) -> FastAPI:
    application = FastAPI(title="Eleições Brasil", lifespan=_lifespan)
    application.state.ports = ports
    application.state.pool_factory = pool_factory or _pool_from_environment
    application.state.session_maker_factory = _session_factory(
        pool_factory,
        session_maker_factory,
    )
    application.include_router(votos_router)
    application.include_router(relatorios_router)
    application.include_router(verticalizacao_router)
    application.add_api_route("/health", health, methods=["GET"], summary="Saúde da API")
    _handlers(application)
    return application


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    if getattr(application.state, "ports", None) is not None:
        yield
        return
    pool = cast(PoolFactory, application.state.pool_factory)()
    await pool.open(wait=True)
    application.state.pool = pool
    maker = _open_sessions(application)
    try:
        yield
    finally:
        await pool.close()
        if maker is not None:
            await maker.dispose()


def build_pool(env: Mapping[str, str]) -> AsyncPool:
    settings = _host_settings(env)
    # open=False: the constructor must not touch the loop; the lifespan awaits open().
    pool = AsyncConnectionPool(postgres_conninfo(settings), open=False, min_size=1, max_size=4)
    return cast(AsyncPool, pool)


def postgres_conninfo(env: Mapping[str, str]) -> str:
    endpoint = database_endpoint(env)
    return make_conninfo(
        host=endpoint.host,
        port=endpoint.port,
        user=endpoint.user,
        password=endpoint.password,
        dbname=endpoint.name,
    )


def build_async_sessions(env: Mapping[str, str]) -> AsyncSessionMaker:
    return AsyncSessionMaker(sqlalchemy_url(_host_settings(env)))


def _pool_from_environment() -> AsyncPool:
    load_dotenv()
    return build_pool(os.environ)


def _sessions_from_environment() -> AsyncSessionMaker:
    load_dotenv()
    return build_async_sessions(os.environ)


def _session_factory(
    pool_factory: PoolFactory | None,
    session_maker_factory: SessionMakerFactory | None,
) -> SessionMakerFactory | None:
    if session_maker_factory is not None:
        return session_maker_factory
    if pool_factory is None:
        return _sessions_from_environment
    return None


def _open_sessions(application: FastAPI) -> AsyncSessionMaker | None:
    factory = application.state.session_maker_factory
    if factory is None:
        application.state.session_maker = None
        return None
    maker = cast(SessionMakerFactory, factory)()
    application.state.session_maker = maker
    return maker


def _handlers(application: FastAPI) -> None:
    application.add_exception_handler(ElectionError, cast(ExceptionHandler, election_error))
    application.add_exception_handler(
        RequestValidationError,
        cast(ExceptionHandler, invalid_request),
    )
    application.add_exception_handler(
        StarletteHTTPException,
        cast(ExceptionHandler, http_exception),
    )
    application.add_exception_handler(Exception, cast(ExceptionHandler, unexpected))


app = create_app()
