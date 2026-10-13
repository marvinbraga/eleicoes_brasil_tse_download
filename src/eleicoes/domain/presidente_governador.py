"""President × governor reading. Classes and margins are derived, not stored."""

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.grade import place_sort_key
from eleicoes.domain.regiao import REGIONS, MacroRegion
from eleicoes.domain.values import UF_CODES, ElectionYear, Turno, Uf, uf_name

_MAX_PARTIDO: Final = 99
_CONSOLIDACAO: Final = "consolidacao"
_VIRADA: Final = "terreno_de_virada"
_ABERTO: Final = "em_aberto"
_SEM: Final = "sem_governador"
CLASS_ORDER: Final[tuple[str, ...]] = (_CONSOLIDACAO, _VIRADA, _ABERTO, _SEM)
CLASS_LABELS: Final[dict[str, str]] = {
    _CONSOLIDACAO: "Consolidação",
    _VIRADA: "Terreno de virada",
    _ABERTO: "Em aberto",
    _SEM: "Sem governador",
}
_COUNTRY_CODE: Final = "BR"
_COUNTRY_NAME: Final = "Brasil"


@dataclass(frozen=True, slots=True)
class PartyTally:
    partido: int
    votos_nominais: int
    votos_legenda: int

    def __post_init__(self) -> None:
        _require_range(self.partido, 0, _MAX_PARTIDO, "partido")
        _require_count(self.votos_nominais, "votos_nominais")
        _require_count(self.votos_legenda, "votos_legenda")
        if self.votos == 0:
            raise InvalidBoletimConsultaError("votos")

    @property
    def votos(self) -> int:
        return self.votos_nominais + self.votos_legenda


@dataclass(frozen=True, slots=True)
class CargoTally:
    parties: tuple[PartyTally, ...]
    branco: int
    nulo: int

    def __post_init__(self) -> None:
        if not self.parties:
            raise InvalidBoletimConsultaError("partido")
        numbers = tuple(party.partido for party in self.parties)
        if len(numbers) != len(set(numbers)):
            raise InvalidBoletimConsultaError("partido")
        _require_count(self.branco, "branco")
        _require_count(self.nulo, "nulo")
        ordered = tuple(sorted(self.parties, key=lambda party: party.partido))
        object.__setattr__(self, "parties", ordered)

    @property
    def valid(self) -> int:
        return sum(party.votos for party in self.parties)


@dataclass(frozen=True, slots=True)
class MunicipalPlace:
    uf: str
    codigo: str
    nome: str
    presidente: CargoTally
    governador: CargoTally | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "uf", Uf(self.uf).code)
        object.__setattr__(self, "codigo", _text(self.codigo, "codigo"))
        object.__setattr__(self, "nome", _text(self.nome, "nome"))
        if not isinstance(self.presidente, CargoTally):
            raise InvalidBoletimConsultaError("presidente")
        if self.governador is not None and not isinstance(self.governador, CargoTally):
            raise InvalidBoletimConsultaError("governador")


@dataclass(frozen=True, slots=True)
class RankedParty:
    partido: int
    votos: int

    def __post_init__(self) -> None:
        _require_range(self.partido, 0, _MAX_PARTIDO, "partido")
        _require_count(self.votos, "votos")
        if self.votos == 0:
            raise InvalidBoletimConsultaError("votos")


@dataclass(frozen=True, slots=True)
class CargoReading:
    leader: RankedParty | None
    runner_up: RankedParty | None
    valid: int
    branco: int
    nulo: int

    def __post_init__(self) -> None:
        _require_count(self.valid, "votos")
        _require_count(self.branco, "branco")
        _require_count(self.nulo, "nulo")
        _require_rank(self.leader, self.runner_up)

    def party_share(self, votos: int) -> Fraction:
        if self.valid == 0:
            return Fraction(0)
        return Fraction(votos, self.valid)

    def ballot_share(self, amount: int) -> Fraction:
        total = self.valid + self.branco + self.nulo
        if total == 0:
            return Fraction(0)
        return Fraction(amount, total)


@dataclass(frozen=True, slots=True)
class PlaceReading:
    codigo: str
    nome: str
    presidente: CargoReading
    governador: CargoReading | None
    classe: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "codigo", _text(self.codigo, "codigo"))
        object.__setattr__(self, "nome", _text(self.nome, "nome"))
        if self.presidente.leader is None:
            raise InvalidBoletimConsultaError("presidente")
        if classify(self.presidente, self.governador) != self.classe:
            raise InvalidBoletimConsultaError("classe")

    @property
    def margin(self) -> Fraction:
        leader = self.presidente.leader
        if leader is None or self.presidente.valid == 0:
            raise InvalidBoletimConsultaError("margem")
        second = 0 if self.presidente.runner_up is None else self.presidente.runner_up.votos
        return Fraction(leader.votos - second, self.presidente.valid)


@dataclass(frozen=True, slots=True)
class ClassSlice:
    classe: str
    cidades: int
    votos_validos: int

    def __post_init__(self) -> None:
        if self.classe not in CLASS_ORDER:
            raise InvalidBoletimConsultaError("classe")
        _require_count(self.cidades, "cidades")
        _require_count(self.votos_validos, "votos_validos")


@dataclass(frozen=True, slots=True)
class Composition:
    classes: tuple[ClassSlice, ...]
    votos_validos: int
    branco: int
    nulo: int

    def __post_init__(self) -> None:
        found = tuple(item.classe for item in self.classes)
        if found != CLASS_ORDER:
            raise InvalidBoletimConsultaError("classe")
        _require_count(self.votos_validos, "votos_validos")
        _require_count(self.branco, "branco")
        _require_count(self.nulo, "nulo")
        if self.votos_validos != sum(item.votos_validos for item in self.classes):
            raise InvalidBoletimConsultaError("votos_validos")

    def share_of(self, classe: str) -> Fraction:
        if self.votos_validos == 0:
            return Fraction(0)
        return Fraction(_slice_votes(self.classes, classe), self.votos_validos)


@dataclass(frozen=True, slots=True)
class CrossReportView:
    ano: int
    turno: int
    composition: Composition
    municipalities: tuple[tuple[str, tuple[PlaceReading, ...]], ...]
    states: tuple[PlaceReading, ...]
    regions: tuple[PlaceReading, ...]
    country: PlaceReading | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ano", ElectionYear(self.ano).value)
        object.__setattr__(self, "turno", Turno(self.turno).value)


def rank_parties(parties: tuple[PartyTally, ...]) -> tuple[RankedParty, ...]:
    ordered = sorted(parties, key=lambda party: (-party.votos, party.partido))
    return tuple(RankedParty(party.partido, party.votos) for party in ordered)


def read_cargo(tally: CargoTally) -> CargoReading:
    ranked = rank_parties(tally.parties)
    runner = ranked[1] if len(ranked) > 1 else None
    return CargoReading(ranked[0], runner, tally.valid, tally.branco, tally.nulo)


def classify(president: CargoReading, governor: CargoReading | None) -> str | None:
    if president.leader is None:
        return None
    if governor is None or governor.leader is None:
        return _SEM
    if governor.leader.partido == president.leader.partido:
        return _CONSOLIDACAO
    return _turnaround(president, governor.leader.partido)


def read_place(place: MunicipalPlace) -> PlaceReading:
    return _as_reading(place.codigo, place.nome, place.presidente, place.governador)


def aggregate_places(
    places: tuple[MunicipalPlace, ...],
    codigo: str,
    nome: str,
) -> PlaceReading:
    if not places:
        raise InvalidBoletimConsultaError("lugar")
    return _as_reading(codigo, nome, _sum_cargo(_presidents(places)), _sum_governor(places))


def composition_of(places: tuple[MunicipalPlace, ...]) -> Composition:
    cities = {classe: 0 for classe in CLASS_ORDER}
    votes = {classe: 0 for classe in CLASS_ORDER}
    branco, nulo = _compose(places, cities, votes)
    total = sum(votes.values())
    slices = tuple(ClassSlice(classe, cities[classe], votes[classe]) for classe in CLASS_ORDER)
    return Composition(slices, total, branco, nulo)


def readings_by_uf(
    places: tuple[MunicipalPlace, ...],
) -> tuple[tuple[str, tuple[PlaceReading, ...]], ...]:
    grouped = _by_uf(places)
    return tuple(_block(grouped, code) for code in UF_CODES if code in grouped)


def state_readings(places: tuple[MunicipalPlace, ...]) -> tuple[PlaceReading, ...]:
    grouped = _by_uf(places)
    rows = tuple(_state_row(grouped, code) for code in UF_CODES)
    return _by_margin(tuple(row for row in rows if row is not None))


def region_readings(places: tuple[MunicipalPlace, ...]) -> tuple[PlaceReading, ...]:
    grouped = _by_uf(places)
    rows = tuple(_region_row(grouped, region) for region in REGIONS)
    return _by_margin(tuple(row for row in rows if row is not None))


def country_reading(places: tuple[MunicipalPlace, ...]) -> PlaceReading | None:
    if not places:
        return None
    return aggregate_places(places, _COUNTRY_CODE, _COUNTRY_NAME)


def view_from_places(
    ano: int,
    turno: int,
    places: tuple[MunicipalPlace, ...],
) -> CrossReportView:
    return CrossReportView(
        ano,
        turno,
        composition_of(places),
        readings_by_uf(places),
        state_readings(places),
        region_readings(places),
        country_reading(places),
    )


def _turnaround(president: CargoReading, partido: int) -> str:
    runner = president.runner_up
    if runner is not None and runner.partido == partido:
        return _VIRADA
    return _ABERTO


def _as_reading(
    codigo: str,
    nome: str,
    president: CargoTally,
    governor: CargoTally | None,
) -> PlaceReading:
    president_reading = read_cargo(president)
    governor_reading = None if governor is None else read_cargo(governor)
    classe = classify(president_reading, governor_reading)
    if classe is None:
        raise InvalidBoletimConsultaError("presidente")
    return PlaceReading(codigo, nome, president_reading, governor_reading, classe)


def _compose(
    places: tuple[MunicipalPlace, ...],
    cities: dict[str, int],
    votes: dict[str, int],
) -> tuple[int, int]:
    branco = 0
    nulo = 0
    for place in places:
        reading = read_place(place)
        cities[reading.classe] += 1
        votes[reading.classe] += reading.presidente.valid
        branco += reading.presidente.branco
        nulo += reading.presidente.nulo
    return branco, nulo


def _presidents(places: tuple[MunicipalPlace, ...]) -> tuple[CargoTally, ...]:
    return tuple(place.presidente for place in places)


def _sum_governor(places: tuple[MunicipalPlace, ...]) -> CargoTally | None:
    found = tuple(place.governador for place in places if place.governador is not None)
    if not found:
        return None
    return _sum_cargo(found)


def _sum_cargo(tallies: tuple[CargoTally, ...]) -> CargoTally:
    nominais: dict[int, int] = {}
    legenda: dict[int, int] = {}
    branco = 0
    nulo = 0
    for tally in tallies:
        branco += tally.branco
        nulo += tally.nulo
        _add_parties(nominais, legenda, tally)
    parties = tuple(
        PartyTally(partido, nominais[partido], legenda[partido]) for partido in sorted(nominais)
    )
    return CargoTally(parties, branco, nulo)


def _add_parties(
    nominais: dict[int, int],
    legenda: dict[int, int],
    tally: CargoTally,
) -> None:
    for party in tally.parties:
        nominais[party.partido] = nominais.get(party.partido, 0) + party.votos_nominais
        legenda[party.partido] = legenda.get(party.partido, 0) + party.votos_legenda


def _by_uf(places: tuple[MunicipalPlace, ...]) -> dict[str, tuple[MunicipalPlace, ...]]:
    grouped: dict[str, list[MunicipalPlace]] = {}
    for place in places:
        grouped.setdefault(place.uf, []).append(place)
    return {code: tuple(items) for code, items in grouped.items()}


def _block(
    grouped: Mapping[str, tuple[MunicipalPlace, ...]],
    code: str,
) -> tuple[str, tuple[PlaceReading, ...]]:
    return code, _by_margin(tuple(read_place(place) for place in grouped[code]))


def _state_row(
    grouped: Mapping[str, tuple[MunicipalPlace, ...]],
    code: str,
) -> PlaceReading | None:
    found = grouped.get(code)
    if found is None:
        return None
    return aggregate_places(found, code, uf_name(code))


def _region_row(
    grouped: Mapping[str, tuple[MunicipalPlace, ...]],
    region: MacroRegion,
) -> PlaceReading | None:
    found = _region_places(grouped, region)
    if not found:
        return None
    return aggregate_places(found, region.sigla, region.name)


def _region_places(
    grouped: Mapping[str, tuple[MunicipalPlace, ...]],
    region: MacroRegion,
) -> tuple[MunicipalPlace, ...]:
    found: list[MunicipalPlace] = []
    for code in region.ufs:
        found.extend(grouped.get(code, ()))
    return tuple(found)


def _by_margin(rows: tuple[PlaceReading, ...]) -> tuple[PlaceReading, ...]:
    return tuple(sorted(rows, key=_margin_key))


def _margin_key(reading: PlaceReading) -> tuple[Fraction, str, str]:
    nome, codigo = place_sort_key(reading.nome, reading.codigo)
    return (reading.margin, nome, codigo)


def _slice_votes(classes: tuple[ClassSlice, ...], classe: str) -> int:
    for item in classes:
        if item.classe == classe:
            return item.votos_validos
    raise InvalidBoletimConsultaError("classe")


def _require_rank(leader: RankedParty | None, runner: RankedParty | None) -> None:
    if leader is None and runner is not None:
        raise InvalidBoletimConsultaError("partido")
    if leader is None or runner is None:
        return
    tied = runner.votos == leader.votos and runner.partido <= leader.partido
    if runner.votos > leader.votos or tied:
        raise InvalidBoletimConsultaError("partido")


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise InvalidBoletimConsultaError(field)
    return value.strip()


def _require_count(value: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidBoletimConsultaError(field)


def _require_range(value: int, lower: int, upper: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidBoletimConsultaError(field)
    if value < lower or value > upper:
        raise InvalidBoletimConsultaError(field)
