"""Sync and async sessions for the existing Postgres URL. The driver is psycopg 3."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Protocol

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from eleicoes.domain.errors import DatabaseConfigError

_KEYS: Final = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
)
_DRIVER: Final = "postgresql+psycopg"
_ASYNC_POOL: Final = 4


@dataclass(frozen=True, slots=True)
class DatabaseEndpoint:
    host: str
    port: int
    user: str
    password: str
    name: str


class SyncSessionFactory(Protocol):
    def __call__(self) -> Session: ...


class AsyncSessionMaker:
    """One async engine for the API process. Each call opens a session; dispose closes the pool."""

    def __init__(self, url: URL) -> None:
        self._engine: AsyncEngine = create_async_engine(url, pool_size=_ASYNC_POOL, max_overflow=0)
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False)

    def __call__(self) -> AsyncSession:
        return self._sessions()

    async def dispose(self) -> None:
        await self._engine.dispose()


def database_endpoint(env: Mapping[str, str]) -> DatabaseEndpoint:
    missing = tuple(key for key in _KEYS if _blank(env.get(key)))
    if missing:
        raise DatabaseConfigError(missing)
    try:
        port = int(env["POSTGRES_PORT"])
    except ValueError as exc:
        raise DatabaseConfigError(("POSTGRES_PORT",)) from exc
    return DatabaseEndpoint(
        host=env["POSTGRES_HOST"],
        port=port,
        user=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
        name=env["POSTGRES_DB"],
    )


def sqlalchemy_url(env: Mapping[str, str]) -> URL:
    endpoint = database_endpoint(env)
    return URL.create(
        drivername=_DRIVER,
        username=endpoint.user,
        password=endpoint.password,
        host=endpoint.host,
        port=endpoint.port,
        database=endpoint.name,
    )


def open_sync_session(env: Mapping[str, str]) -> Session:
    engine = create_engine(sqlalchemy_url(env), poolclass=NullPool)
    return Session(engine, expire_on_commit=False)


def _blank(value: str | None) -> bool:
    return value is None or value.strip() == ""
