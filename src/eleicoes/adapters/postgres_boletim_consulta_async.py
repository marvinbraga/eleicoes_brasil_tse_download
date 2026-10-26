"""Async boletim reader. It executes the same SQL as PostgresBoletimReader."""

from collections.abc import Sequence

from eleicoes.adapters.async_query import fetch_all
from eleicoes.adapters.postgres_boletim_consulta import (
    _BLANK_NULL,
    _BLANKS,
    _COMPARISON,
    _LEADING,
    _LINES,
    _NOMINAL,
    _PARTICIPATION,
    _PARTY_POWER,
    _PRESENT_UFS,
    _RANKING,
    _SECTION_VOTES,
    _SECTIONS,
    _TOTALS,
    _ZONES,
    _blank,
    _brancos,
    _comparativo,
    _linha,
    _municipio,
    _nominal,
    _participacao,
    _poder,
    _primeiro,
    _section,
    _total,
    _uf_code,
    _zona,
    votos_por_secao,
)
from eleicoes.domain.boletim_consulta import (
    BlankNullProjection,
    BrancosNulos,
    Comparativo,
    LinhaVoto,
    NominalProjection,
    Participacao,
    PoderPartido,
    PrimeiroColocado,
    SectionProjection,
    TotalCargo,
    VotosMunicipio,
    VotosSecao,
    VotosZona,
)
from eleicoes.domain.errors import InvalidNivelError
from eleicoes.ports.async_sql import AsyncSqlConnection


class AsyncPostgresBoletimReader:
    def __init__(self, connection: AsyncSqlConnection) -> None:
        self._connection = connection

    async def totals(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[TotalCargo, ...]:
        rows = await self._rows(_TOTALS, (ano, turno, uf, cargo))
        return tuple(_total(row) for row in rows)

    async def municipalities(
        self, ano: int, turno: int, uf: str, cargo: str, numero: int
    ) -> tuple[VotosMunicipio, ...]:
        params = (ano, turno, uf, cargo, ano, turno, uf, cargo, numero)
        return tuple(_municipio(row) for row in await self._rows(_RANKING, params))

    async def comparison(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        primeiro: int,
        segundo: int,
        nivel: str,
    ) -> tuple[Comparativo, ...]:
        sql = _sql_for(_COMPARISON, nivel)
        params = (
            ano,
            turno,
            uf,
            cargo,
            ano,
            turno,
            uf,
            cargo,
            primeiro,
            segundo,
            primeiro,
            segundo,
        )
        return tuple(_comparativo(row, nivel) for row in await self._rows(sql, params))

    async def party_power(
        self, ano: int, turno: int, ufs: tuple[str, ...], cargo: str, nivel: str
    ) -> tuple[PoderPartido, ...]:
        sql = _sql_for(_PARTY_POWER, nivel)
        states = list(ufs)
        params = (ano, turno, states, cargo, ano, turno, states, cargo)
        return tuple(_poder(row, nivel) for row in await self._rows(sql, params))

    async def participation(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[Participacao, ...]:
        sql = _sql_for(_PARTICIPATION, nivel)
        params = (ano, turno, uf, cargo)
        return tuple(_participacao(row, nivel) for row in await self._rows(sql, params))

    async def blank_and_null(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[BrancosNulos, ...]:
        sql = _sql_for(_BLANK_NULL, nivel)
        params = (ano, turno, uf, cargo, ano, turno, uf, cargo)
        return tuple(_brancos(row, nivel) for row in await self._rows(sql, params))

    async def leading_candidate(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[PrimeiroColocado, ...]:
        sql = _sql_for(_LEADING, nivel)
        params = (ano, turno, uf, cargo, ano, turno, uf, cargo)
        return tuple(_primeiro(row, nivel) for row in await self._rows(sql, params))

    async def section_lines(
        self, ano: int, turno: int, uf: str, municipio: int, zona: int, secao: int
    ) -> tuple[LinhaVoto, ...]:
        params = (ano, turno, uf, municipio, zona, secao)
        return tuple(_linha(row) for row in await self._rows(_LINES, params))

    async def zones(
        self, ano: int, turno: int, uf: str, municipio: int, cargo: str, numero: int
    ) -> tuple[VotosZona, ...]:
        params = (ano, turno, uf, municipio, cargo, ano, turno, uf, municipio, cargo, numero)
        return tuple(_zona(row) for row in await self._rows(_ZONES, params))

    async def section_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[SectionProjection, ...]:
        rows = await self._rows(_SECTIONS, (ano, turno, uf, cargo))
        return tuple(_section(row) for row in rows)

    async def nominal_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[NominalProjection, ...]:
        rows = await self._rows(_NOMINAL, (ano, turno, uf, cargo))
        return tuple(_nominal(row) for row in rows)

    async def blank_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[BlankNullProjection, ...]:
        rows = await self._rows(_BLANKS, (ano, turno, uf, cargo))
        return tuple(_blank(row) for row in rows)

    async def section_votes(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[VotosSecao, ...]:
        params = (ano, turno, uf, cargo)
        return votos_por_secao(await self._rows(_SECTION_VOTES, params))

    async def present_ufs(self, ano: int, turno: int, cargo: str) -> tuple[str, ...]:
        rows = await self._rows(_PRESENT_UFS, (ano, turno, cargo))
        return tuple(_uf_code(row) for row in rows)

    async def _rows(self, sql: str, params: Sequence[object]) -> tuple[tuple[object, ...], ...]:
        return await fetch_all(self._connection, sql, params)


def _sql_for(queries: dict[str, str], nivel: str) -> str:
    sql = queries.get(nivel)
    if sql is None:
        raise InvalidNivelError(nivel)
    return sql
