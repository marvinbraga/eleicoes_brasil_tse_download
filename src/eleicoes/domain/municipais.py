"""Prefeito vigente, vereadores eleitos e eleitorado apto por município. Sem IO."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Final

from eleicoes.domain.errors import DuplicateMayorError, InvalidMunicipalRowError
from eleicoes.domain.importing import ImportReport
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS

CARGO_PREFEITO: Final = 11
CARGO_VEREADOR: Final = 13
TIPO_SUPLEMENTAR: Final = 1
TIPO_ORDINARIA: Final = 2
PRIMEIRO_TURNO: Final = 1
SIT_ELEITO: Final = 1
SITUACOES_VEREADOR_ELEITO: Final = frozenset({1, 2, 3})

Key = tuple[str, str]


@dataclass(frozen=True, slots=True)
class CandidateRow:
    uf: str
    ue: str
    nome_ue: str
    tipo_eleicao: int
    data_eleicao: date
    turno: int
    cargo: int
    sq_candidato: str
    nome_urna: str
    partido: int
    sigla: str
    situacao: int


@dataclass(frozen=True, slots=True)
class ElectorateRow:
    uf: str
    ue: str
    nome_ue: str
    tipo_eleicao: int
    turno: int
    cargo: int
    aptos: int


@dataclass(frozen=True, slots=True)
class SeatRow:
    uf: str
    ue: str
    tipo_eleicao: int
    cargo: int
    vagas: int


@dataclass(frozen=True, slots=True)
class MunicipalRaw:
    geracao: str
    candidatos: tuple[CandidateRow, ...]
    eleitorado: tuple[ElectorateRow, ...]
    vagas: tuple[SeatRow, ...]


@dataclass(frozen=True, slots=True)
class Mayor:
    partido: int
    sigla: str
    nome_urna: str
    sq_candidato: str
    data_eleicao: date
    turno: int
    suplementar: bool


@dataclass(frozen=True, slots=True)
class MunicipalityResult:
    uf: str
    ue: str
    nome: str
    eleitorado: int
    vagas_vereador: int
    prefeito: Mayor | None


@dataclass(frozen=True, slots=True)
class CouncilSeats:
    uf: str
    ue: str
    partido: int
    sigla: str
    eleitos: int


@dataclass(frozen=True, slots=True)
class SeatGap:
    uf: str
    ue: str
    eleitos: int
    vagas: int


@dataclass(frozen=True, slots=True)
class MunicipalBuild:
    geracao: str
    municipios: tuple[MunicipalityResult, ...]
    vereadores: tuple[CouncilSeats, ...]
    divergencias: tuple[SeatGap, ...]

    @property
    def prefeitos(self) -> int:
        return sum(1 for item in self.municipios if item.prefeito is not None)

    @property
    def sem_prefeito(self) -> int:
        return len(self.municipios) - self.prefeitos

    @property
    def suplementares(self) -> int:
        return sum(
            1 for item in self.municipios if item.prefeito is not None and item.prefeito.suplementar
        )

    @property
    def vereadores_eleitos(self) -> int:
        return sum(item.eleitos for item in self.vereadores)


def parse_tse_date(text: str, field: str) -> date:
    try:
        return datetime.strptime(text, "%d/%m/%Y").date()
    except ValueError as exc:
        raise InvalidMunicipalRowError(field) from exc


def parse_int(text: str, field: str) -> int:
    try:
        return int(text)
    except ValueError as exc:
        raise InvalidMunicipalRowError(field) from exc


def build_municipal_results(raw: MunicipalRaw) -> MunicipalBuild:
    names, electorate = _electorate(raw.eleitorado)
    for row in raw.candidatos:
        names.setdefault((row.uf, row.ue), row.nome_ue)
    mayors = _mayors(raw.candidatos)
    seats = _ordinary_seats(raw.vagas)
    council = _council(raw.candidatos)
    elected: Counter[Key] = Counter()
    for item in council:
        elected[(item.uf, item.ue)] += item.eleitos
    municipios = tuple(
        MunicipalityResult(
            uf=key[0],
            ue=key[1],
            nome=names.get(key, ""),
            eleitorado=electorate.get(key, 0),
            vagas_vereador=seats.get(key, 0),
            prefeito=mayors.get(key),
        )
        for key in sorted(set(names) | set(mayors))
    )
    gaps = tuple(
        SeatGap(key[0], key[1], elected.get(key, 0), seats.get(key, 0))
        for key in sorted(set(seats) | set(elected))
        if elected.get(key, 0) != seats.get(key, 0)
    )
    return MunicipalBuild(raw.geracao, municipios, council, gaps)


def _electorate(rows: Iterable[ElectorateRow]) -> tuple[dict[Key, str], dict[Key, int]]:
    names: dict[Key, str] = {}
    totals: dict[Key, int] = {}
    for row in rows:
        if (
            row.cargo != CARGO_PREFEITO
            or row.tipo_eleicao != TIPO_ORDINARIA
            or row.turno != PRIMEIRO_TURNO
        ):
            continue
        key = (row.uf, row.ue)
        names[key] = row.nome_ue
        totals[key] = totals.get(key, 0) + row.aptos
    return names, totals


def _rank(row: CandidateRow) -> tuple[date, int]:
    return (row.data_eleicao, row.turno)


def _mayors(rows: Iterable[CandidateRow]) -> dict[Key, Mayor]:
    grouped: dict[Key, list[CandidateRow]] = {}
    for row in rows:
        if row.cargo == CARGO_PREFEITO and row.situacao == SIT_ELEITO:
            grouped.setdefault((row.uf, row.ue), []).append(row)
    chosen: dict[Key, Mayor] = {}
    for key, linhas in grouped.items():
        top = max(_rank(linha) for linha in linhas)
        winners = {linha.sq_candidato: linha for linha in linhas if _rank(linha) == top}
        if len(winners) != 1:
            raise DuplicateMayorError(*key)
        row = next(iter(winners.values()))
        chosen[key] = Mayor(
            partido=row.partido,
            sigla=row.sigla,
            nome_urna=row.nome_urna,
            sq_candidato=row.sq_candidato,
            data_eleicao=row.data_eleicao,
            turno=row.turno,
            suplementar=row.tipo_eleicao == TIPO_SUPLEMENTAR,
        )
    return chosen


def _ordinary_seats(rows: Iterable[SeatRow]) -> dict[Key, int]:
    seats: dict[Key, int] = {}
    for row in rows:
        if row.cargo == CARGO_VEREADOR and row.tipo_eleicao == TIPO_ORDINARIA:
            key = (row.uf, row.ue)
            seats[key] = max(seats.get(key, 0), row.vagas)
    return seats


def _council(rows: Iterable[CandidateRow]) -> tuple[CouncilSeats, ...]:
    counts: Counter[tuple[str, str, int]] = Counter()
    siglas: dict[tuple[str, str, int], str] = {}
    for row in rows:
        if row.cargo != CARGO_VEREADOR or row.situacao not in SITUACOES_VEREADOR_ELEITO:
            continue
        key = (row.uf, row.ue, row.partido)
        counts[key] += 1
        siglas[key] = min(siglas.get(key, row.sigla), row.sigla)
    return tuple(
        CouncilSeats(uf, ue, partido, siglas[(uf, ue, partido)], counts[(uf, ue, partido)])
        for uf, ue, partido in sorted(counts)
    )


@dataclass(frozen=True, slots=True)
class MunicipalImportReport:
    """faltando lista os membros por UF que não carregaram; sem eles a análise não é refeita."""

    tables: ImportReport
    results: MunicipalBuild | None
    faltando: tuple[str, ...] = ()

    @property
    def exit_code(self) -> int:
        if self.tables.exit_code != EXIT_SUCCESS:
            return self.tables.exit_code
        if self.faltando:
            return EXIT_FAILURE
        return EXIT_SUCCESS
