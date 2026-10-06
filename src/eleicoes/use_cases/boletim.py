"""Boletim consultations. Each class is one question, not a shared facade."""

from dataclasses import replace
from fractions import Fraction

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
from eleicoes.domain.values import ElectionYear, Turno, Uf
from eleicoes.ports.boletim_consulta import BoletimReader


class SummarizeCargo:
    def __init__(self, reader: BoletimReader) -> None:
        self._reader = reader

    def execute(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[TotalCargo, ...]:
        year, turn, code = _scope(ano, turno, uf)
        office = require_cargo(cargo)
        rows = self._reader.totals(year, turn, code, office)
        return tuple(sorted(rows, key=_total_key))


class RankMunicipalities:
    def __init__(self, reader: BoletimReader) -> None:
        self._reader = reader

    def execute(
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
        rows = self._reader.municipalities(year, turn, code, office, candidate)
        key = _most_key if order.value == "mais" else _least_key
        return tuple(sorted(rows, key=key))


class CompareCandidates:
    def __init__(self, reader: BoletimReader) -> None:
        self._reader = reader

    def execute(
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
        rows = self._reader.comparison(year, turn, code, office, first, second, level.value)
        return tuple(sorted(rows, key=_comparison_key))


class ListPartyPower:
    def __init__(self, reader: BoletimReader) -> None:
        self._reader = reader

    def execute(
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
        rows = self._reader.party_power(year, turn, scope.ufs, office, level.value)
        counted = tuple(row for row in rows if partido_tem_candidato(office, row.partido))
        return tuple(sorted(_with_region(counted, scope.regiao), key=_party_power_key))


class ListParticipation:
    def __init__(self, reader: BoletimReader) -> None:
        self._reader = reader

    def execute(
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
        rows = self._reader.participation(year, turn, code, office, level.value)
        return tuple(sorted(rows, key=_participation_key))


class ListBlankAndNull:
    def __init__(self, reader: BoletimReader) -> None:
        self._reader = reader

    def execute(
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
        rows = self._reader.blank_and_null(year, turn, code, office, level.value)
        return tuple(sorted(rows, key=_blank_key))


class ListLeadingCandidate:
    def __init__(self, reader: BoletimReader) -> None:
        self._reader = reader

    def execute(
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
        rows = self._reader.leading_candidate(year, turn, code, office, level.value)
        return tuple(sorted(rows, key=_leader_key))


class ListSectionVotes:
    def __init__(self, reader: BoletimReader) -> None:
        self._reader = reader

    def execute(
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
        rows = self._reader.section_lines(year, turn, code, city, zone, section)
        return tuple(sorted(rows, key=_line_key))


class ListVotesByZone:
    def __init__(self, reader: BoletimReader) -> None:
        self._reader = reader

    def execute(
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
        rows = self._reader.zones(year, turn, code, city, office, candidate)
        return tuple(sorted(rows, key=lambda row: row.zona))


class ListBulletinFindings:
    def __init__(self, reader: BoletimReader) -> None:
        self._reader = reader

    def execute(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[IndicioBoletim, ...]:
        year, turn, code = _scope(ano, turno, uf)
        office = require_cargo(cargo)
        return evaluate_findings(
            code,
            office,
            self._reader.section_projections(year, turn, code, office),
            self._reader.nominal_projections(year, turn, code, office),
            self._reader.blank_projections(year, turn, code, office),
        )


def _scope(ano: int, turno: int, uf: str) -> tuple[int, int, str]:
    return ElectionYear(ano).value, Turno(turno).value, Uf(uf).code


def _total_key(row: TotalCargo) -> tuple[str, int]:
    numero = -1 if row.numero is None else row.numero
    return (row.tipo_voto, numero)


def _most_key(row: VotosMunicipio) -> tuple[int, int]:
    return (-row.quantidade, row.municipio)


def _least_key(row: VotosMunicipio) -> tuple[int, int]:
    return (row.quantidade, row.municipio)


def _comparison_key(row: Comparativo) -> tuple[int, int, int]:
    zona = -1 if row.zona is None else row.zona
    secao = -1 if row.secao is None else row.secao
    return (row.municipio, zona, secao)


def _with_region(rows: tuple[PoderPartido, ...], regiao: str | None) -> tuple[PoderPartido, ...]:
    if regiao is None:
        return rows
    return tuple(replace(row, regiao=regiao) for row in rows)


def _party_power_key(row: PoderPartido) -> tuple[int, int, int, int]:
    return (row.municipio or 0, row.zona or 0, -row.votos, row.partido)


def _participation_key(row: Participacao) -> tuple[int, int]:
    return (row.municipio, row.zona or 0)


def _blank_key(row: BrancosNulos) -> tuple[Fraction, int, int]:
    share = Fraction(0) if row.comparecimento == 0 else Fraction(row.votos, row.comparecimento)
    return (-share, row.municipio, row.zona or 0)


def _leader_key(row: PrimeiroColocado) -> tuple[int, int, int]:
    return (-row.votos, row.municipio, row.zona or 0)


def _line_key(row: LinhaVoto) -> tuple[str, int, str, int]:
    numero = -1 if row.numero is None else row.numero
    return (row.cargo, row.ordem_impressao, row.tipo_voto, numero)
