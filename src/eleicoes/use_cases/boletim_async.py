"""Async boletim questions. Sorting and filters stay in the synchronous use cases."""

from eleicoes.domain.boletim_consulta import (
    BrancosNulos,
    Comparativo,
    ComparisonLevel,
    IndicioBoletim,
    LinhaVoto,
    Participacao,
    PartyLevel,
    PlaceLevel,
    PoderPartido,
    PrimeiroColocado,
    RankingOrder,
    TotalCargo,
    VotosMunicipio,
    VotosZona,
    partido_tem_candidato,
    require_cargo,
    require_municipio,
    require_numero,
    require_secao,
    require_zona,
)
from eleicoes.domain.boletim_indicio import evaluate_findings
from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.use_cases.boletim import (
    _blank_key,
    _comparison_key,
    _leader_key,
    _least_key,
    _line_key,
    _most_key,
    _participation_key,
    _party_power_key,
    _scope,
    _total_key,
    _with_region,
)


class SummarizeCargo:
    def __init__(self, reader: AsyncBoletimReader) -> None:
        self._reader = reader

    async def execute(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[TotalCargo, ...]:
        year, turn, code = _scope(ano, turno, uf)
        office = require_cargo(cargo)
        rows = await self._reader.totals(year, turn, code, office)
        return tuple(sorted(rows, key=_total_key))


class RankMunicipalities:
    def __init__(self, reader: AsyncBoletimReader) -> None:
        self._reader = reader

    async def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        numero: int,
        ordem: str = "mais",
    ) -> tuple[VotosMunicipio, ...]:
        year, turn, code = _scope(ano, turno, uf)
        office = require_cargo(cargo)
        candidate = require_numero(numero)
        order = RankingOrder(ordem)
        rows = await self._reader.municipalities(year, turn, code, office, candidate)
        key = _most_key if order.value == "mais" else _least_key
        return tuple(sorted(rows, key=key))


class CompareCandidates:
    def __init__(self, reader: AsyncBoletimReader) -> None:
        self._reader = reader

    async def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        primeiro: int,
        segundo: int,
        nivel: str = "municipio",
    ) -> tuple[Comparativo, ...]:
        year, turn, code = _scope(ano, turno, uf)
        office = require_cargo(cargo)
        first = require_numero(primeiro)
        second = require_numero(segundo)
        level = ComparisonLevel(nivel)
        rows = await self._reader.comparison(year, turn, code, office, first, second, level.value)
        return tuple(sorted(rows, key=_comparison_key))


class ListPartyPower:
    def __init__(self, reader: AsyncBoletimReader) -> None:
        self._reader = reader

    async def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        nivel: str = "municipio",
    ) -> tuple[PoderPartido, ...]:
        year, turn, code = _scope(ano, turno, uf)
        office = require_cargo(cargo)
        level = PartyLevel(nivel)
        scope = level.scope(code)
        rows = await self._reader.party_power(year, turn, scope.ufs, office, level.value)
        counted = tuple(row for row in rows if partido_tem_candidato(office, row.partido))
        return tuple(sorted(_with_region(counted, scope.regiao), key=_party_power_key))


class ListParticipation:
    def __init__(self, reader: AsyncBoletimReader) -> None:
        self._reader = reader

    async def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        nivel: str = "municipio",
    ) -> tuple[Participacao, ...]:
        year, turn, code = _scope(ano, turno, uf)
        office = require_cargo(cargo)
        level = PlaceLevel(nivel)
        rows = await self._reader.participation(year, turn, code, office, level.value)
        return tuple(sorted(rows, key=_participation_key))


class ListBlankAndNull:
    def __init__(self, reader: AsyncBoletimReader) -> None:
        self._reader = reader

    async def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        nivel: str = "municipio",
    ) -> tuple[BrancosNulos, ...]:
        year, turn, code = _scope(ano, turno, uf)
        office = require_cargo(cargo)
        level = PlaceLevel(nivel)
        rows = await self._reader.blank_and_null(year, turn, code, office, level.value)
        return tuple(sorted(rows, key=_blank_key))


class ListLeadingCandidate:
    def __init__(self, reader: AsyncBoletimReader) -> None:
        self._reader = reader

    async def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        nivel: str = "municipio",
    ) -> tuple[PrimeiroColocado, ...]:
        year, turn, code = _scope(ano, turno, uf)
        office = require_cargo(cargo)
        level = PlaceLevel(nivel)
        rows = await self._reader.leading_candidate(year, turn, code, office, level.value)
        return tuple(sorted(rows, key=_leader_key))


class ListSectionVotes:
    def __init__(self, reader: AsyncBoletimReader) -> None:
        self._reader = reader

    async def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        municipio: int,
        zona: int,
        secao: int,
    ) -> tuple[LinhaVoto, ...]:
        year, turn, code = _scope(ano, turno, uf)
        city = require_municipio(municipio)
        zone = require_zona(zona)
        section = require_secao(secao)
        rows = await self._reader.section_lines(year, turn, code, city, zone, section)
        return tuple(sorted(rows, key=_line_key))


class ListVotesByZone:
    def __init__(self, reader: AsyncBoletimReader) -> None:
        self._reader = reader

    async def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        municipio: int,
        cargo: str,
        numero: int,
    ) -> tuple[VotosZona, ...]:
        year, turn, code = _scope(ano, turno, uf)
        city = require_municipio(municipio)
        office = require_cargo(cargo)
        candidate = require_numero(numero)
        rows = await self._reader.zones(year, turn, code, city, office, candidate)
        return tuple(sorted(rows, key=lambda row: row.zona))


class ListBulletinFindings:
    def __init__(self, reader: AsyncBoletimReader) -> None:
        self._reader = reader

    async def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
    ) -> tuple[IndicioBoletim, ...]:
        year, turn, code = _scope(ano, turno, uf)
        office = require_cargo(cargo)
        return evaluate_findings(
            code,
            office,
            await self._reader.section_projections(year, turn, code, office),
            await self._reader.nominal_projections(year, turn, code, office),
            await self._reader.blank_projections(year, turn, code, office),
        )
