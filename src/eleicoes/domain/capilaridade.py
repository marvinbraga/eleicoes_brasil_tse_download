"""Where a party's votes come from among the municipalities of one scope. Pure and exact."""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Final

from eleicoes.domain.errors import (
    InconsistentCellError,
    InvalidCargoError,
    InvalidRecorteError,
    InvalidUfError,
)
from eleicoes.domain.regiao import REGIONS, region_of
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.domain.values import UF_NAMES, Uf, uf_name

CARGOS: Final[frozenset[str]] = frozenset(
    {"presidente", "governador", "senador", "deputadoFederal", "deputadoEstadual"}
)
ABROAD: Final = "ZZ"
PAIS: Final = "pais"
REGIAO: Final = "regiao"
UF: Final = "uf"
_MUNICIPIO: Final = "municipio"
_SUFFIX: Final = re.compile(r" \(([A-Z]{2})\)$")
# TSE codes of the 27 capitals, checked read-only in analise.relatorio_poder_linha on 2026-10-22.
CAPITAIS: Final[frozenset[str]] = frozenset(
    {
        "1392",
        "27855",
        "6050",
        "2550",
        "38490",
        "13897",
        "97012",
        "57053",
        "93734",
        "9210",
        "90670",
        "90514",
        "41238",
        "4278",
        "20516",
        "75353",
        "25313",
        "12190",
        "60011",
        "17612",
        "88013",
        "35",
        "3018",
        "81051",
        "71072",
        "31054",
        "73440",
    }
)


def require_capillarity_cargo(cargo: str) -> str:
    if cargo not in CARGOS:
        raise InvalidCargoError(cargo)
    return cargo


@dataclass(frozen=True, slots=True)
class Municipality:
    codigo: str
    nome: str
    uf: str
    votos: Mapping[int, int]
    validos: int = field(init=False)

    def __post_init__(self) -> None:
        copied = dict(self.votos)
        if any(count < 0 for count in copied.values()):
            raise InconsistentCellError()
        object.__setattr__(self, "votos", copied)
        object.__setattr__(self, "validos", sum(copied.values()))

    def of(self, partido: int) -> int:
        return self.votos.get(partido, 0)


@dataclass(frozen=True, slots=True)
class MunicipalSet:
    places: tuple[Municipality, ...]
    exterior: int


def places_from_cells(cells: Iterable[StoredCell]) -> MunicipalSet:
    grouped: dict[str, list[StoredCell]] = {}
    for cell in cells:
        if cell.nivel != _MUNICIPIO:
            raise InconsistentCellError()
        grouped.setdefault(cell.codigo, []).append(cell)
    built = tuple(_place(codigo, items) for codigo, items in grouped.items())
    kept = sorted((p for p in built if p.uf != ABROAD), key=lambda p: (p.nome.casefold(), p.codigo))
    return MunicipalSet(tuple(kept), len(built) - len(kept))


def _place(codigo: str, cells: list[StoredCell]) -> Municipality:
    nome = cells[0].nome
    if any(cell.nome != nome for cell in cells):
        raise InconsistentCellError()
    votos: dict[int, int] = {}
    for cell in cells:
        if cell.partido in votos:
            raise InconsistentCellError()
        votos[cell.partido] = cell.votos_nominais + cell.votos_legenda
    return Municipality(codigo, nome, uf_of(nome), votos)


def uf_of(nome: str) -> str:
    found = _SUFFIX.search(nome)
    if found is None:
        raise InconsistentCellError()
    try:
        return Uf(found.group(1)).code
    except InvalidUfError as exc:
        raise InconsistentCellError() from exc


@dataclass(frozen=True, slots=True)
class Scope:
    tipo: str
    codigo: str
    nome: str


BRASIL: Final = Scope(PAIS, "BR", "Brasil")


def scope_of(regiao: str | None, uf: str | None) -> Scope:
    if regiao is not None and uf is not None:
        raise InvalidRecorteError()
    if regiao is not None:
        return _region_scope(regiao)
    if uf is not None:
        return _uf_scope(uf)
    return BRASIL


def _region_scope(sigla: str) -> Scope:
    wanted = sigla.strip().upper()
    for region in REGIONS:
        if region.sigla == wanted:
            return Scope(REGIAO, region.sigla, region.name)
    raise InvalidRecorteError()


def _uf_scope(code: str) -> Scope:
    normalized = Uf(code).code
    if normalized == ABROAD:
        raise InvalidRecorteError()
    return Scope(UF, normalized, uf_name(normalized))


def all_scopes() -> tuple[Scope, ...]:
    regions = tuple(Scope(REGIAO, region.sigla, region.name) for region in REGIONS)
    codes = sorted(code for code in UF_NAMES if code != ABROAD)
    return (BRASIL, *regions, *(Scope(UF, code, uf_name(code)) for code in codes))


def contains(scope: Scope, place: Municipality) -> bool:
    if scope.tipo == PAIS:
        return True
    if scope.tipo == REGIAO:
        return region_of(place.uf).sigla == scope.codigo
    return place.uf == scope.codigo


def subdivision_of(scope: Scope, place: Municipality) -> tuple[str, str] | None:
    if scope.tipo == PAIS:
        region = region_of(place.uf)
        return region.sigla, region.name
    if scope.tipo == REGIAO:
        return place.uf, uf_name(place.uf)
    return None


PRESENCA: Final = Fraction(5, 100)
DESTAQUES: Final = 5
BAND_KEYS: Final[tuple[str, ...]] = (
    "zero",
    "ate_metade",
    "metade_a_media",
    "media_a_1_5",
    "1_5_a_2",
    "2_a_3",
    "3_ou_mais",
)
_BAND_EDGES: Final[tuple[Fraction, ...]] = (
    Fraction(1, 2),
    Fraction(1),
    Fraction(3, 2),
    Fraction(2),
    Fraction(3),
)


def _ratio(numerator: int, denominator: int) -> Fraction:
    if denominator == 0:
        return Fraction(0)
    return Fraction(numerator, denominator)


@dataclass(frozen=True, slots=True)
class Share:
    municipios: int
    votos: int
    validos: int
    parte: Fraction
    eleitorado: Fraction

    @property
    def vezes(self) -> Fraction:
        if self.eleitorado == 0:
            return Fraction(0)
        return self.parte / self.eleitorado


@dataclass(frozen=True, slots=True)
class Subdivision:
    codigo: str
    nome: str
    share: Share


@dataclass(frozen=True, slots=True)
class Band:
    chave: str
    municipios: int
    validos: int
    votos: int


@dataclass(frozen=True, slots=True)
class PlaceStrength:
    codigo: str
    nome: str
    votos: int
    validos: int

    @property
    def fatia(self) -> Fraction:
        return _ratio(self.votos, self.validos)


@dataclass(frozen=True, slots=True)
class PartyMetrics:
    partido: int
    votos: int
    validos: int
    validos_recorte: int
    ufs_com_voto: int
    municipios: int
    indice: Fraction
    top10: Share
    presenca: int
    capitais: Share | None
    subdivisoes: tuple[Subdivision, ...]
    faixas: tuple[Band, ...]
    fortes: tuple[PlaceStrength, ...]
    maiores: tuple[PlaceStrength, ...]

    @property
    def fatia(self) -> Fraction:
        return _ratio(self.votos, self.validos)

    @property
    def fatia_recorte(self) -> Fraction:
        return _ratio(self.votos, self.validos_recorte)

    @property
    def presenca_parte(self) -> Fraction:
        return _ratio(self.presenca, self.municipios)


def concentration_index(rows: Sequence[tuple[int, int]]) -> Fraction:
    """Gini of the party's votes against valid votes, places sorted by the party's share."""
    total = sum(validos for validos, _votos in rows)
    party = sum(votos for _validos, votos in rows)
    if total == 0 or party == 0:
        return Fraction(0)
    ordered = sorted((row for row in rows if row[0] > 0), key=lambda row: Fraction(row[1], row[0]))
    cumulative = 0
    area = 0
    for validos, votos in ordered:
        previous = cumulative
        cumulative += votos
        area += validos * (previous + cumulative)
    return 1 - Fraction(area, total * party)


def share(rows: Sequence[Municipality], partido: int, party_total: int, valid_total: int) -> Share:
    votos = sum(place.of(partido) for place in rows)
    validos = sum(place.validos for place in rows)
    return Share(
        len(rows), votos, validos, _ratio(votos, party_total), _ratio(validos, valid_total)
    )


def party_metrics(partido: int, scope: Scope, members: Sequence[Municipality]) -> PartyMetrics:
    counted = tuple(place for place in members if place.validos > 0)
    ufs = frozenset(place.uf for place in counted if place.of(partido) > 0)
    universe = tuple(place for place in counted if place.uf in ufs)
    votos = sum(place.of(partido) for place in universe)
    validos = sum(place.validos for place in universe)
    if votos == 0:
        raise InconsistentCellError()
    strong = _by_strength(universe, partido)
    return PartyMetrics(
        partido,
        votos,
        validos,
        sum(place.validos for place in counted),
        len(ufs),
        len(universe),
        concentration_index(tuple((place.validos, place.of(partido)) for place in universe)),
        share(strong[: _top_count(len(strong))], partido, votos, validos),
        sum(1 for place in universe if Fraction(place.of(partido), place.validos) >= PRESENCA),
        _capitals(universe, partido, votos, validos),
        _subdivisions(scope, counted, partido, votos),
        _bands(universe, partido, votos, validos),
        tuple(_strength(place, partido) for place in strong[:DESTAQUES]),
        _largest(universe, partido),
    )


def _top_count(total: int) -> int:
    return max(1, -(-total // 10))


def _by_strength(rows: Sequence[Municipality], partido: int) -> tuple[Municipality, ...]:
    def key(place: Municipality) -> tuple[Fraction, int, tuple[int, str]]:
        share = Fraction(place.of(partido), place.validos)
        return (-share, -place.of(partido), code_order(place.codigo))

    return tuple(sorted(rows, key=key))


def _capitals(
    universe: Sequence[Municipality], partido: int, votos: int, validos: int
) -> Share | None:
    found = tuple(place for place in universe if place.codigo in CAPITAIS)
    if not found:
        return None
    return share(found, partido, votos, validos)


def _subdivisions(
    scope: Scope, counted: Sequence[Municipality], partido: int, votos: int
) -> tuple[Subdivision, ...]:
    total = sum(place.validos for place in counted)
    grouped: dict[tuple[str, str], list[Municipality]] = {}
    for place in counted:
        key = subdivision_of(scope, place)
        if key is not None:
            grouped.setdefault(key, []).append(place)
    built = (
        Subdivision(code, name, share(rows, partido, votos, total))
        for (code, name), rows in grouped.items()
    )
    return tuple(sorted(built, key=lambda item: (-item.share.parte, item.codigo)))


def _bands(
    universe: Sequence[Municipality], partido: int, votos: int, validos: int
) -> tuple[Band, ...]:
    counts = [[0, 0, 0] for _key in BAND_KEYS]
    for place in universe:
        slot = counts[_band_index(place.of(partido), place.validos, votos, validos)]
        slot[0] += 1
        slot[1] += place.validos
        slot[2] += place.of(partido)
    return tuple(
        Band(key, slot[0], slot[1], slot[2]) for key, slot in zip(BAND_KEYS, counts, strict=True)
    )


def _band_index(party: int, valid: int, party_total: int, valid_total: int) -> int:
    if party == 0:
        return 0
    relative = Fraction(party * valid_total, valid * party_total)
    return 1 + sum(1 for edge in _BAND_EDGES if relative >= edge)


def _largest(universe: Sequence[Municipality], partido: int) -> tuple[PlaceStrength, ...]:
    voted = (place for place in universe if place.of(partido) > 0)
    ordered = sorted(voted, key=lambda place: (-place.of(partido), code_order(place.codigo)))
    return tuple(_strength(place, partido) for place in ordered[:DESTAQUES])


def code_order(codigo: str) -> tuple[int, str]:
    """Numeric order for TSE codes stored without leading zeros ("9" before "10")."""
    return (len(codigo), codigo)


def _strength(place: Municipality, partido: int) -> PlaceStrength:
    return PlaceStrength(place.codigo, place.nome, place.of(partido), place.validos)
