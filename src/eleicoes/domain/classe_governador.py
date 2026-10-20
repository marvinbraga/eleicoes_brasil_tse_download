"""Governor class from the presidential mix. The class rule stays in classify."""

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.errors import (
    FewClassesError,
    FewMunicipalitiesError,
    FewStatesError,
    InconsistentCellError,
    MissingCrossReportError,
)
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
_MIN_STATES: Final = 2
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
    uf: str
    leader: int

    def __post_init__(self) -> None:
        if self.label not in CLASS_ORDER:
            raise InconsistentCellError()
        object.__setattr__(self, "uf", _text(self.uf))
        _count(self.leader)
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
    without_uf: int

    def __post_init__(self) -> None:
        _count(self.without_uf)

    def matrix(self) -> tuple[tuple[float, ...], ...]:
        return tuple(_floats(place.vector(self.parties)) for place in self.places)

    def labels(self) -> tuple[str, ...]:
        return tuple(place.label for place in self.places)

    def groups(self) -> tuple[str, ...]:
        return tuple(place.uf for place in self.places)


@dataclass(frozen=True, slots=True)
class ClassOutcome:
    classe: str
    support: int
    rules: tuple[tuple[RuleCut, ...], ...]
    recall: Fraction


@dataclass(frozen=True, slots=True)
class UfScore:
    uf: str
    municipios: int
    hit_rate: Fraction

    def __post_init__(self) -> None:
        object.__setattr__(self, "uf", _text(self.uf))
        if self.municipios <= 0:
            raise InconsistentCellError()


@dataclass(frozen=True, slots=True)
class ClassReport:
    ano: int
    turno: int
    parties: tuple[int, ...]
    hit_rate: Fraction
    baseline: Fraction
    rows: tuple[ClassOutcome, ...]
    held_out: tuple[str, ...]
    leader_baseline: Fraction
    macro_f1: Fraction
    by_uf: tuple[UfScore, ...]
    without_uf: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "ano", ElectionYear(self.ano).value)
        object.__setattr__(self, "turno", Turno(self.turno).value)
        _count(self.without_uf)

    @property
    def below_baseline(self) -> bool:
        return self.hit_rate < max(self.baseline, self.leader_baseline)


def class_places(
    lines: tuple[ClassLine, ...],
    ufs: tuple[tuple[str, str], ...],
) -> tuple[ClassPlace, ...]:
    places, _orphans = _placed(lines, ufs)
    return places


def prepare_class_dataset(
    lines: tuple[ClassLine, ...],
    ufs: tuple[tuple[str, str], ...],
) -> ClassDataset:
    if not ufs:
        raise MissingCrossReportError()
    places, orphans = _placed(lines, ufs)
    if len(places) < _MIN_PLACES:
        raise FewMunicipalitiesError()
    dataset = _separate(places, orphans)
    if len(set(dataset.groups())) < _MIN_STATES:
        raise FewStatesError()
    return dataset


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
    predicted: tuple[str, ...],
    rules: tuple[ClassRule, ...],
) -> ClassReport:
    places = dataset.places
    _check_prediction(places, predicted)
    if len({place.uf for place in places}) < _MIN_STATES:
        raise FewStatesError()
    expected = dataset.labels()
    rows = tuple(_outcome(classe, expected, predicted, rules) for classe in _present(places))
    return ClassReport(
        ano,
        turno,
        dataset.parties,
        _hit_rate(expected, predicted),
        _baseline(places, _majority_guess),
        rows,
        dataset.held_out,
        _baseline(places, _leader_guess),
        _macro_f1(expected, predicted, rows),
        _by_uf(places, predicted),
        dataset.without_uf,
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


@dataclass(frozen=True, slots=True)
class _Draft:
    codigo: str
    nome: str
    comparecimento: int
    label: str
    votes: tuple[tuple[int, int], ...]
    leader: int

    def place(self, uf: str) -> ClassPlace:
        return ClassPlace(
            self.codigo,
            self.nome,
            self.comparecimento,
            self.label,
            self.votes,
            uf,
            self.leader,
        )


def _placed(
    lines: tuple[ClassLine, ...],
    ufs: tuple[tuple[str, str], ...],
) -> tuple[tuple[ClassPlace, ...], int]:
    states = _states(ufs)
    grouped = _by_place(lines)
    found: list[ClassPlace] = []
    orphans = 0
    for codigo in sorted(grouped):
        draft = _draft(grouped[codigo])
        if draft is None:
            continue
        uf = states.get(codigo)
        if uf is None:
            orphans += 1
            continue
        found.append(draft.place(uf))
    return tuple(found), orphans


def _states(ufs: tuple[tuple[str, str], ...]) -> dict[str, str]:
    found: dict[str, str] = {}
    for raw_codigo, raw_uf in ufs:
        uf = _text(raw_uf)
        previous = found.setdefault(_text(raw_codigo), uf)
        if previous != uf:
            raise InconsistentCellError()
    return found


def _draft(sides: Mapping[str, _Bag]) -> _Draft | None:
    president = sides.get(_PRESIDENTE)
    governor = sides.get(_GOVERNADOR)
    if president is None or governor is None or president.comparecimento <= 0:
        return None
    reading = _reading(_tally(president))
    label = classify(reading, _reading(_tally(governor)))
    if label is None or reading.leader is None:
        return None
    return _Draft(
        president.codigo,
        president.nome,
        president.comparecimento,
        label,
        _votes(president),
        reading.leader.partido,
    )


def _reading(tally: CargoTally | None) -> CargoReading:
    if tally is None:
        return CargoReading(None, None, 0, 0, 0)
    return read_cargo(tally)


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


def _separate(places: tuple[ClassPlace, ...], orphans: int) -> ClassDataset:
    counts = Counter(place.label for place in places)
    held = tuple(classe for classe in CLASS_ORDER if 0 < counts[classe] < _MIN_CLASS)
    kept = tuple(place for place in places if counts[place.label] >= _MIN_CLASS)
    if len({place.label for place in kept}) < _MIN_CLASS:
        raise FewClassesError()
    if len(kept) < _MIN_PLACES:
        raise FewMunicipalitiesError()
    return ClassDataset(_parties(kept), kept, held, orphans)


def _parties(places: tuple[ClassPlace, ...]) -> tuple[int, ...]:
    numbers = {party for place in places for party, votos in place.votes if votos > 0}
    if not numbers:
        raise FewMunicipalitiesError()
    return tuple(sorted(numbers))


def _present(places: tuple[ClassPlace, ...]) -> tuple[str, ...]:
    found = {place.label for place in places}
    return tuple(classe for classe in CLASS_ORDER if classe in found)


def _check_prediction(places: tuple[ClassPlace, ...], predicted: tuple[str, ...]) -> None:
    if not places or len(places) != len(predicted):
        raise InconsistentCellError()
    if any(label not in CLASS_ORDER for label in predicted):
        raise InconsistentCellError()


def _hit_rate(expected: tuple[str, ...], predicted: tuple[str, ...]) -> Fraction:
    hits = sum(1 for left, right in zip(expected, predicted, strict=True) if left == right)
    return Fraction(hits, len(expected))


_Guess = Callable[[ClassPlace], str]


def _baseline(
    places: tuple[ClassPlace, ...],
    learn: Callable[[tuple[ClassPlace, ...]], _Guess],
) -> Fraction:
    hits = 0
    for uf in sorted({place.uf for place in places}):
        guess = learn(tuple(place for place in places if place.uf != uf))
        hits += sum(1 for place in places if place.uf == uf and guess(place) == place.label)
    return Fraction(hits, len(places))


def _majority_guess(train: tuple[ClassPlace, ...]) -> _Guess:
    label = majority_label(tuple(place.label for place in train))
    return lambda _place: label


def _leader_guess(train: tuple[ClassPlace, ...]) -> _Guess:
    fallback = majority_label(tuple(place.label for place in train))
    by_leader: dict[int, list[str]] = {}
    for place in train:
        by_leader.setdefault(place.leader, []).append(place.label)
    table = {leader: majority_label(tuple(labels)) for leader, labels in by_leader.items()}
    return lambda place: table.get(place.leader, fallback)


def _by_uf(places: tuple[ClassPlace, ...], predicted: tuple[str, ...]) -> tuple[UfScore, ...]:
    totals: Counter[str] = Counter()
    hits: Counter[str] = Counter()
    for place, label in zip(places, predicted, strict=True):
        totals[place.uf] += 1
        hits[place.uf] += int(place.label == label)
    return tuple(UfScore(uf, totals[uf], Fraction(hits[uf], totals[uf])) for uf in sorted(totals))


def _outcome(
    classe: str,
    expected: tuple[str, ...],
    predicted: tuple[str, ...],
    rules: tuple[ClassRule, ...],
) -> ClassOutcome:
    support = sum(1 for label in expected if label == classe)
    cuts = tuple(rule.cuts for rule in rules if rule.classe == classe)
    return ClassOutcome(
        classe, support, cuts, Fraction(_hits(classe, expected, predicted), support)
    )


def _hits(classe: str, expected: tuple[str, ...], predicted: tuple[str, ...]) -> int:
    pairs = zip(expected, predicted, strict=True)
    return sum(1 for left, right in pairs if left == classe and right == classe)


def _macro_f1(
    expected: tuple[str, ...],
    predicted: tuple[str, ...],
    rows: tuple[ClassOutcome, ...],
) -> Fraction:
    scores = tuple(_f1(row, _precision(row.classe, expected, predicted)) for row in rows)
    return sum(scores, Fraction(0)) / len(scores)


def _precision(classe: str, expected: tuple[str, ...], predicted: tuple[str, ...]) -> Fraction:
    guessed = sum(1 for label in predicted if label == classe)
    if guessed == 0:
        return Fraction(0)
    return Fraction(_hits(classe, expected, predicted), guessed)


def _f1(row: ClassOutcome, precision: Fraction) -> Fraction:
    total = precision + row.recall
    if total == 0:
        return Fraction(0)
    return 2 * precision * row.recall / total


def _floats(shares: tuple[Fraction, ...]) -> tuple[float, ...]:
    return tuple(float(share) for share in shares)


def _text(value: object) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise InconsistentCellError()
    return value.strip()


def _count(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InconsistentCellError()
