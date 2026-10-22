"""Readable spread class per party, the view per scope, and the summary the scoreboard reuses."""

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.capilaridade import (
    Municipality,
    MunicipalSet,
    PartyMetrics,
    Scope,
    Subdivision,
    all_scopes,
    contains,
    party_metrics,
    require_capillarity_cargo,
    scope_of,
)
from eleicoes.domain.errors import EmptyRecorteError, MissingPowerReportError
from eleicoes.domain.percentual import round_half_up
from eleicoes.domain.values import ElectionYear, Turno

POUCO_VOTO: Final = Fraction(1, 100)
MIN_MUNICIPIOS: Final = 20
CAPITAIS_VEZES: Final = Fraction(7, 4)
REGIONAL_PARTE: Final = Fraction(1, 2)
REGIONAL_VEZES: Final = Fraction(3, 2)
POUCOS_PARTE: Final = Fraction(1, 2)
POUCOS_VEZES: Final = Fraction(2)
CLASSES: Final[tuple[str, ...]] = (
    "pouco_voto",
    "sem_base",
    "capitais",
    "regional",
    "poucos_municipios",
    "espalhado",
)
UNRANKED: Final[frozenset[str]] = frozenset({"pouco_voto", "sem_base"})


@dataclass(frozen=True, slots=True)
class Classification:
    classe: str
    subdivisao: Subdivision | None = None


def classify(metrics: PartyMetrics) -> Classification:
    if metrics.fatia < POUCO_VOTO:
        return Classification("pouco_voto")
    if metrics.municipios < MIN_MUNICIPIOS:
        return Classification("sem_base")
    capitals = metrics.capitais
    if capitals is not None and capitals.vezes >= CAPITAIS_VEZES:
        return Classification("capitais")
    dominant = _dominant(metrics.subdivisoes)
    if dominant is not None:
        return Classification("regional", dominant)
    top = metrics.top10
    if top.parte >= POUCOS_PARTE and top.vezes >= POUCOS_VEZES:
        return Classification("poucos_municipios")
    return Classification("espalhado")


def _dominant(items: Sequence[Subdivision]) -> Subdivision | None:
    for item in items:
        if item.share.parte >= REGIONAL_PARTE and item.share.vezes >= REGIONAL_VEZES:
            return item
    return None


@dataclass(frozen=True, slots=True)
class ClassifiedParty:
    metrics: PartyMetrics
    classificacao: Classification


@dataclass(frozen=True, slots=True)
class CapillarityView:
    scope: Scope
    municipios: int
    ufs: int
    sem_validos: int
    validos: int
    partidos: tuple[ClassifiedParty, ...]


def build_view(scope: Scope, places: Sequence[Municipality]) -> CapillarityView | None:
    members = tuple(place for place in places if contains(scope, place))
    counted = tuple(place for place in members if place.validos > 0)
    if not counted:
        return None
    parties = sorted({party for place in counted for party, n in place.votos.items() if n > 0})
    built = (_classified(party, scope, members) for party in parties)
    ranked = tuple(sorted(built, key=_rank_key))
    validos = sum(place.validos for place in counted)
    ufs = len({place.uf for place in counted})
    missing = len(members) - len(counted)
    return CapillarityView(scope, len(counted), ufs, missing, validos, ranked)


def _classified(partido: int, scope: Scope, members: Sequence[Municipality]) -> ClassifiedParty:
    metrics = party_metrics(partido, scope, members)
    return ClassifiedParty(metrics, classify(metrics))


def _rank_key(item: ClassifiedParty) -> tuple[bool, Fraction, int]:
    unranked = item.classificacao.classe in UNRANKED
    return (unranked, -item.metrics.indice, item.metrics.partido)


@dataclass(frozen=True, slots=True)
class CapillarityReport:
    ano: int
    turno: int
    cargo: str
    exterior: int
    views: tuple[CapillarityView, ...]

    def view(self, regiao: str | None, uf: str | None) -> CapillarityView:
        scope = scope_of(regiao, uf)
        for item in self.views:
            if item.scope == scope:
                return item
        raise EmptyRecorteError(scope.nome, self.cargo)


def build_report(ano: int, turno: int, cargo: str, municipal: MunicipalSet) -> CapillarityReport:
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    office = require_capillarity_cargo(cargo)
    if not municipal.places:
        raise MissingPowerReportError(office)
    built = (build_view(scope, municipal.places) for scope in all_scopes())
    views = tuple(view for view in built if view is not None)
    return CapillarityReport(year, turn, office, municipal.exterior, views)


@dataclass(frozen=True, slots=True)
class PartySummary:
    partido: int
    votos: int
    fatia: Fraction
    indice: Fraction
    presenca: Fraction
    ufs_com_voto: int
    classe: str

    @property
    def indice_100(self) -> int:
        return round_half_up(self.indice * 100)


def summarize(view: CapillarityView) -> tuple[PartySummary, ...]:
    return tuple(
        PartySummary(
            item.metrics.partido,
            item.metrics.votos,
            item.metrics.fatia,
            item.metrics.indice,
            item.metrics.presenca_parte,
            item.metrics.ufs_com_voto,
            item.classificacao.classe,
        )
        for item in view.partidos
    )
