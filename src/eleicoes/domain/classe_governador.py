"""Governor class from the presidential mix. The class rule stays in classify."""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.errors import FewClassesError, FewMunicipalitiesError, InconsistentCellError
from eleicoes.domain.presidente_governador import (
    CLASS_ORDER,
    CargoReading,
    CargoTally,
    PartyTally,
    classify,
    read_cargo,
)
from eleicoes.domain.values import ElectionYear, Turno

_MIN_PLACES: Final = 3
_MIN_CLASS: Final = 2
_CARGOS: Final = frozenset({"presidente", "governador"})
_PRESIDENTE: Final = "presidente"
_GOVERNADOR: Final = "governador"


@dataclass(frozen=True, slots=True)
class ClassLine:
    cargo: str
    codigo: str
    nome: str
    comparecimento: int
    partido: int
    votos_nominais: int
    votos_legenda: int

    def __post_init__(self) -> None:
        if self.cargo not in _CARGOS:
            raise InconsistentCellError()
        object.__setattr__(self, "codigo", _text(self.codigo))
        object.__setattr__(self, "nome", _text(self.nome))
        _count(self.comparecimento)
        _count(self.partido)
        _count(self.votos_nominais)
        _count(self.votos_legenda)


@dataclass(frozen=True, slots=True)
class ClassPlace:
    codigo: str
    nome: str
    comparecimento: int
    label: str
    votes: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        if self.label not in CLASS_ORDER:
            raise InconsistentCellError()
        if self.comparecimento <= 0:
            raise InconsistentCellError()
        parties = tuple(party for party, _votes in self.votes)
        if len(parties) != len(set(parties)):
            raise InconsistentCellError()

    def vector(self, parties: tuple[int, ...]) -> tuple[Fraction, ...]:
        found = dict(self.votes)
        valid = sum(found.values())
        if valid <= 0:
            raise InconsistentCellError()
        return tuple(Fraction(found.get(party, 0), valid) for party in parties)


@dataclass(frozen=True, slots=True)
class RuleCut:
    party: int
    threshold: float
    at_most: bool


@dataclass(frozen=True, slots=True)
class ClassRule:
    classe: str
    cuts: tuple[RuleCut, ...]

    def __post_init__(self) -> None:
        if self.classe not in CLASS_ORDER:
            raise InconsistentCellError()


@dataclass(frozen=True, slots=True)
class ClassDataset:
    parties: tuple[int, ...]
    places: tuple[ClassPlace, ...]
    held_out: tuple[str, ...]

    def matrix(self) -> tuple[tuple[float, ...], ...]:
        return tuple(_floats(place.vector(self.parties)) for place in self.places)

    def labels(self) -> tuple[str, ...]:
        return tuple(place.label for place in self.places)


@dataclass(frozen=True, slots=True)
class ClassOutcome:
    classe: str
    support: int
    rules: tuple[tuple[RuleCut, ...], ...]


@dataclass(frozen=True, slots=True)
class ClassReport:
    ano: int
    turno: int
    parties: tuple[int, ...]
    hit_rate: Fraction
    baseline: Fraction
    rows: tuple[ClassOutcome, ...]
    held_out: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ano", ElectionYear(self.ano).value)
        object.__setattr__(self, "turno", Turno(self.turno).value)


def class_places(lines: tuple[ClassLine, ...]) -> tuple[ClassPlace, ...]:
    grouped = _by_place(lines)
    found: list[ClassPlace] = []
    for codigo in sorted(grouped):
        place = _one(grouped[codigo])
        if place is not None:
            found.append(place)
    return tuple(found)


def prepare_class_dataset(lines: tuple[ClassLine, ...]) -> ClassDataset:
    places = class_places(lines)
    if len(places) < _MIN_PLACES:
        raise FewMunicipalitiesError()
    return _separate(places)


def majority_label(labels: tuple[str, ...]) -> str:
    if not labels:
        raise FewClassesError()
    counts = Counter(labels)
    best = max(counts.values())
    for classe in CLASS_ORDER:
        if counts.get(classe, 0) == best:
            return classe
    raise FewClassesError()


def class_report(
    ano: int,
    turno: int,
    dataset: ClassDataset,
    majority: str,
    expected: tuple[str, ...],
    predicted: tuple[str, ...],
    rules: tuple[ClassRule, ...],
) -> ClassReport:
    if not expected or len(expected) != len(predicted) or majority not in CLASS_ORDER:
        raise InconsistentCellError()
    total = len(expected)
    hits = sum(1 for left, right in zip(expected, predicted, strict=True) if left == right)
    base = sum(1 for label in expected if label == majority)
    present = _present(dataset.places)
    rows = tuple(_outcome(classe, expected, rules) for classe in present)
    return ClassReport(
        ano,
        turno,
        dataset.parties,
        Fraction(hits, total),
        Fraction(base, total),
        rows,
        dataset.held_out,
    )


class _Bag:
    def __init__(self, line: ClassLine) -> None:
        self.codigo = line.codigo
        self.nome = line.nome
        self.comparecimento = line.comparecimento
        self.nominais: dict[int, int] = {}
        self.legenda: dict[int, int] = {}
        self._add(line)

    def accept(self, line: ClassLine) -> None:
        if line.nome != self.nome or line.comparecimento != self.comparecimento:
            raise InconsistentCellError()
        self._add(line)

    def _add(self, line: ClassLine) -> None:
        self._put(self.nominais, line.partido, line.votos_nominais)
        self._put(self.legenda, line.partido, line.votos_legenda)

    def _put(self, store: dict[int, int], party: int, amount: int) -> None:
        previous = store.get(party)
        if previous is not None and previous != amount:
            raise InconsistentCellError()
        if previous is None:
            store[party] = amount


def _by_place(lines: tuple[ClassLine, ...]) -> dict[str, dict[str, _Bag]]:
    found: dict[str, dict[str, _Bag]] = {}
    for line in lines:
        sides = found.setdefault(line.codigo, {})
        bag = sides.get(line.cargo)
        if bag is None:
            sides[line.cargo] = _Bag(line)
            continue
        bag.accept(line)
    return found


def _one(sides: Mapping[str, _Bag]) -> ClassPlace | None:
    president = sides.get(_PRESIDENTE)
    governor = sides.get(_GOVERNADOR)
    if president is None or governor is None:
        return None
    return _labeled(president, governor)


def _labeled(president: _Bag, governor: _Bag) -> ClassPlace | None:
    if president.comparecimento <= 0:
        return None
    president_tally = _tally(president)
    if president_tally is None:
        return None
    return ClassPlace(
        president.codigo,
        president.nome,
        president.comparecimento,
        _classe(president_tally, _tally(governor)),
        _votes(president),
    )


def _classe(president: CargoTally, governor: CargoTally | None) -> str:
    governor_reading = _reading(governor)
    label = classify(read_cargo(president), governor_reading)
    if label is None:
        raise InconsistentCellError()
    return label


def _reading(governor: CargoTally | None) -> CargoReading | None:
    if governor is None:
        return CargoReading(None, None, 0, 0, 0)
    return read_cargo(governor)


def _tally(bag: _Bag) -> CargoTally | None:
    parties: list[PartyTally] = []
    numbers = sorted(set(bag.nominais) | set(bag.legenda))
    for partido in numbers:
        nominais = bag.nominais.get(partido, 0)
        legenda = bag.legenda.get(partido, 0)
        if nominais + legenda == 0:
            continue
        parties.append(PartyTally(partido, nominais, legenda))
    if not parties:
        return None
    return CargoTally(tuple(parties), 0, 0)


def _votes(bag: _Bag) -> tuple[tuple[int, int], ...]:
    numbers = sorted(set(bag.nominais) | set(bag.legenda))
    rows = tuple(
        (partido, bag.nominais.get(partido, 0) + bag.legenda.get(partido, 0)) for partido in numbers
    )
    return tuple((partido, votos) for partido, votos in rows if votos > 0)


def _separate(places: tuple[ClassPlace, ...]) -> ClassDataset:
    counts = Counter(place.label for place in places)
    held = tuple(classe for classe in CLASS_ORDER if 0 < counts[classe] < _MIN_CLASS)
    kept = tuple(place for place in places if counts[place.label] >= _MIN_CLASS)
    if len({place.label for place in kept}) < _MIN_CLASS:
        raise FewClassesError()
    if len(kept) < _MIN_PLACES:
        raise FewMunicipalitiesError()
    return ClassDataset(_parties(kept), kept, held)


def _parties(places: tuple[ClassPlace, ...]) -> tuple[int, ...]:
    numbers = {party for place in places for party, votos in place.votes if votos > 0}
    if not numbers:
        raise FewMunicipalitiesError()
    return tuple(sorted(numbers))


def _present(places: tuple[ClassPlace, ...]) -> tuple[str, ...]:
    found = {place.label for place in places}
    return tuple(classe for classe in CLASS_ORDER if classe in found)


def _outcome(
    classe: str,
    expected: tuple[str, ...],
    rules: tuple[ClassRule, ...],
) -> ClassOutcome:
    support = sum(1 for label in expected if label == classe)
    cuts = tuple(rule.cuts for rule in rules if rule.classe == classe)
    return ClassOutcome(classe, support, cuts)


def _floats(shares: tuple[Fraction, ...]) -> tuple[float, ...]:
    return tuple(float(share) for share in shares)


def _text(value: object) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise InconsistentCellError()
    return value.strip()


def _count(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InconsistentCellError()
