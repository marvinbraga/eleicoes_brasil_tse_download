"""FastAPI factory. The pool opens in the lifespan and closes on shutdown."""

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
from eleicoes.adapters.http.votos import router as votos_router
from eleicoes.composition.correspondencia import _host_settings
from eleicoes.domain.errors import DatabaseConfigError, ElectionError
from eleicoes.ports.async_sql import AsyncPool

_KEYS = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
)
PoolFactory = Callable[[], AsyncPool]


def create_app(
    ports: ReadPorts | None = None,
    pool_factory: PoolFactory | None = None,
) -> FastAPI:
    application = FastAPI(title="Eleições Brasil", lifespan=_lifespan)
    application.state.ports = ports
    application.state.pool_factory = pool_factory or _pool_from_environment
    application.include_router(votos_router)
    application.include_router(relatorios_router)
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
    try:
        yield
    finally:
        await pool.close()


def build_pool(env: Mapping[str, str]) -> AsyncPool:
    settings = _host_settings(env)
    # open=False: the constructor must not touch the loop; the lifespan awaits open().
    pool = AsyncConnectionPool(postgres_conninfo(settings), open=False, min_size=1, max_size=4)
    return cast(AsyncPool, pool)


def postgres_conninfo(env: Mapping[str, str]) -> str:
    missing = tuple(key for key in _KEYS if _blank(env.get(key)))
    if missing:
        raise DatabaseConfigError(missing)
    try:
        port = int(env["POSTGRES_PORT"])
    except ValueError as exc:
        raise DatabaseConfigError(("POSTGRES_PORT",)) from exc
    return make_conninfo(
        host=env["POSTGRES_HOST"],
        port=port,
        user=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
        dbname=env["POSTGRES_DB"],
    )


def _pool_from_environment() -> AsyncPool:
    load_dotenv()
    return build_pool(os.environ)


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


def _blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


app = create_app()
