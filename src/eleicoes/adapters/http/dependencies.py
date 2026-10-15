"""One pooled connection for boletim and one async ORM session for the report stores."""

from collections.abc import AsyncIterator, Callable
from typing import Annotated, TypeAlias, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from eleicoes.adapters.http.bundle import ReadPorts
from eleicoes.adapters.orm.sessions import AsyncSessionMaker
from eleicoes.adapters.postgres_boletim_consulta_async import AsyncPostgresBoletimReader
from eleicoes.adapters.postgres_municipio_async import AsyncPostgresMunicipalityNames
from eleicoes.adapters.postgres_relatorio_poder_async import AsyncPostgresPowerReportStore
from eleicoes.adapters.postgres_relatorio_presidente_governador_async import (
    AsyncPostgresPresidentGovernorStore,
)
from eleicoes.domain.classe_governador import ClassReport
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.perfis import ProfileReport
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


async def get_session(request: Request) -> AsyncIterator[AsyncSession | None]:
    if _installed(request) is not None:
        yield None
        return
    session = _require_sessions(request)()
    try:
        yield session
    finally:
        await session.close()


SessionDep = Annotated[AsyncSession | None, Depends(get_session)]


async def get_boletim_reader(request: Request, connection: Connection) -> AsyncBoletimReader:
    installed = _installed(request)
    if installed is not None:
        return installed.boletim
    return AsyncPostgresBoletimReader(cast(AsyncSqlConnection, connection))


async def get_municipality_names(
    request: Request,
    session: SessionDep,
) -> AsyncMunicipalityNames:
    installed = _installed(request)
    if installed is not None:
        return installed.names
    return AsyncPostgresMunicipalityNames(_required_session(session))


async def get_power_store(request: Request, session: SessionDep) -> AsyncRelatorioPoderStore:
    installed = _installed(request)
    if installed is not None:
        return installed.power_store
    return AsyncPostgresPowerReportStore(_required_session(session))


async def get_cross_store(
    request: Request,
    session: SessionDep,
) -> AsyncRelatorioPresidenteGovernadorStore:
    installed = _installed(request)
    if installed is not None:
        return installed.cross_store
    return AsyncPostgresPresidentGovernorStore(_required_session(session))


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


def _require_sessions(request: Request) -> AsyncSessionMaker:
    found = getattr(request.app.state, "session_maker", None)
    if not isinstance(found, AsyncSessionMaker):
        raise ElectionError("database session is not configured")
    return found


def _required_session(session: AsyncSession | None) -> AsyncSession:
    if session is None:
        raise ElectionError("database session is not configured")
    return session


ProfileJob: TypeAlias = Callable[[int, int, str, str], ProfileReport]
ClassJob: TypeAlias = Callable[[int, int], ClassReport]


def get_profile_job() -> ProfileJob:
    return _stored_profile


def get_class_job() -> ClassJob:
    return _stored_class


def _stored_profile(ano: int, turno: int, cargo: str, grupos: str) -> ProfileReport:
    from eleicoes.use_cases.apresentar_perfis import (
        _production_clusterer,
        _production_reader,
        build_profile,
    )

    reader = _production_reader()
    try:
        return build_profile(reader, _production_clusterer(), ano, turno, cargo, grupos)
    finally:
        reader.close()


def _stored_class(ano: int, turno: int) -> ClassReport:
    from eleicoes.use_cases.apresentar_classe_governador import (
        _production_model,
        _production_reader,
        build_governor_class,
    )

    reader = _production_reader()
    try:
        return build_governor_class(reader, _production_model(), ano, turno)
    finally:
        reader.close()
