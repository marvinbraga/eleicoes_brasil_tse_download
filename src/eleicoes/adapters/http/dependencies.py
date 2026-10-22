"""One pooled connection for boletim and one async ORM session for the report stores."""

from collections.abc import AsyncIterator, Callable
from functools import lru_cache
from typing import Annotated, Final, TypeAlias, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from eleicoes.adapters.http.bundle import ReadPorts
from eleicoes.adapters.orm.sessions import AsyncSessionMaker
from eleicoes.adapters.postgres_boletim_consulta_async import AsyncPostgresBoletimReader
from eleicoes.adapters.postgres_municipais_async import (
    AsyncPostgresMunicipalReader,
    PooledMunicipalReader,
)
from eleicoes.adapters.postgres_municipio_async import AsyncPostgresMunicipalityNames
from eleicoes.adapters.postgres_relatorio_cadeiras_async import AsyncPostgresSeatVoteStore
from eleicoes.adapters.postgres_relatorio_poder_async import AsyncPostgresPowerReportStore
from eleicoes.adapters.postgres_relatorio_presidente_governador_async import (
    AsyncPostgresPresidentGovernorStore,
)
from eleicoes.domain.classe_governador import ClassReport
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.perfis import ProfileReport, parse_group_span, require_profile_cargo
from eleicoes.ports.async_sql import AsyncPool, AsyncSqlConnection
from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.ports.cadeiras import AsyncEstimativaCadeiras
from eleicoes.ports.grade import AsyncMunicipalityNames
from eleicoes.ports.municipais import AsyncMunicipalResultsReader
from eleicoes.ports.municipal_2024 import AsyncMunicipal2024
from eleicoes.ports.relatorio_cadeiras import AsyncSeatVoteStore
from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore
from eleicoes.ports.relatorio_presidente_governador import AsyncRelatorioPresidenteGovernadorStore
from eleicoes.use_cases.estimativa_cadeiras import StoredSeatEstimates
from eleicoes.use_cases.municipal_2024_placar import StoredMunicipal2024


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


async def get_seat_store(request: Request, session: SessionDep) -> AsyncSeatVoteStore:
    installed = _installed(request)
    if installed is not None:
        if installed.seat_store is None:
            raise ElectionError("seat store is not installed")
        return installed.seat_store
    return AsyncPostgresSeatVoteStore(_required_session(session))


async def get_municipal_reader(
    request: Request,
    connection: Connection,
) -> AsyncMunicipalResultsReader:
    installed = _installed(request)
    if installed is not None:
        if installed.municipais is None:
            raise ElectionError("municipal reader is not installed")
        return installed.municipais
    return AsyncPostgresMunicipalReader(cast(AsyncSqlConnection, connection))


async def get_seat_estimates(
    request: Request,
    session: SessionDep,
) -> AsyncEstimativaCadeiras | None:
    """The scoreboard's optional seat source; installed ports may leave it out (None).

    It shares the request session with get_power_store, so its reads must stay sequential
    with the power reads (never asyncio.gather on one AsyncSession).
    """
    installed = _installed(request)
    if installed is not None:
        return installed.seat_estimates
    return StoredSeatEstimates(AsyncPostgresSeatVoteStore(_required_session(session)))


async def get_municipal_2024(request: Request) -> AsyncMunicipal2024 | None:
    """The scoreboard's optional 2024 source; installed ports may leave it out (None).

    It borrows a pooled connection only while it reads, not for the whole request.
    """
    installed = _installed(request)
    if installed is not None:
        return installed.municipal_2024
    return StoredMunicipal2024(PooledMunicipalReader(_require_pool(request)))


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


# Built reports stay in memory per key. clear_report_caches drops them after the API
# regenerates the base reports; a regeneration from the CLI needs an API restart.
_STORED_REPORTS: Final = 32
ProfileJob: TypeAlias = Callable[[int, int, str, str], ProfileReport]
ClassJob: TypeAlias = Callable[[int, int], ClassReport]


def get_profile_job() -> ProfileJob:
    return _stored_profile


def get_class_job() -> ClassJob:
    return _stored_class


def clear_report_caches() -> None:
    _built_profile.cache_clear()
    _stored_class.cache_clear()


def _stored_profile(ano: int, turno: int, cargo: str, grupos: str) -> ProfileReport:
    return _built_profile(ano, turno, require_profile_cargo(cargo), _canonical_span(grupos))


def _canonical_span(grupos: str) -> str:
    span = parse_group_span(grupos)
    if span.searched:
        return f"{span.lower}-{span.upper}"
    return f"{span.lower}"


@lru_cache(maxsize=_STORED_REPORTS)
def _built_profile(ano: int, turno: int, cargo: str, grupos: str) -> ProfileReport:
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


@lru_cache(maxsize=_STORED_REPORTS)
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
