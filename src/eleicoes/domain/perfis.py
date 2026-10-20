"""Municipal profile vectors. Shares stay here; the fit lives behind a port."""

from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.errors import (
    CargoSemCelulasError,
    EmptyStoredCellsError,
    FewMunicipalitiesError,
    InconsistentCellError,
    InvalidCargoError,
    InvalidGroupSpanError,
)
from eleicoes.domain.grade import place_sort_key
from eleicoes.domain.values import ElectionYear, Turno

_MIN_K: Final = 2
_MAX_K: Final = 10
_MIN_PLACES: Final = 3
_MAX_PARTY: Final = 99
_PROFILE_CARGOS: Final = frozenset({"presidente", "governador", "senador"})
_BALLOT_CARGOS: Final = frozenset({"presidente", "governador"})
_DEPUTY_TEXT: Final = {
    "deputadoFederal": "O cargo deputado federal não tem células gravadas.",
    "deputadoEstadual": "O cargo deputado estadual não tem células gravadas.",
    "deputadoDistrital": "O cargo deputado distrital não tem células gravadas.",
}


@dataclass(frozen=True, slots=True)
class GroupSpan:
    lower: int
    upper: int
    searched: bool

    def __post_init__(self) -> None:
        if isinstance(self.lower, bool) or isinstance(self.upper, bool):
            raise InvalidGroupSpanError()
        if self.lower < _MIN_K or self.upper < self.lower:
            raise InvalidGroupSpanError()
        if self.upper > _MAX_K:
            raise InvalidGroupSpanError()
        if not self.searched and self.lower != self.upper:
            raise InvalidGroupSpanError()

    def values(self) -> tuple[int, ...]:
        return tuple(range(self.lower, self.upper + 1))


@dataclass(frozen=True, slots=True)
class ProfileLine:
    codigo: str
    nome: str
    comparecimento: int
    partido: int
    votos_nominais: int
    votos_legenda: int
    branco: int | None = None
    nulo: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "codigo", _text(self.codigo))
        object.__setattr__(self, "nome", _text(self.nome))
        _count(self.comparecimento)
        _party(self.partido)
        _count(self.votos_nominais)
        _count(self.votos_legenda)
        if (self.branco is None) != (self.nulo is None):
            raise InconsistentCellError()
        _optional_count(self.branco)
        _optional_count(self.nulo)


@dataclass(frozen=True, slots=True)
class ProfilePlace:
    codigo: str
    nome: str
    comparecimento: int
    votes: tuple[int, ...]
    branco: int | None
    nulo: int | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "codigo", _text(self.codigo))
        object.__setattr__(self, "nome", _text(self.nome))
        _count(self.comparecimento)
        _votes(self.votes)
        if (self.branco is None) != (self.nulo is None):
            raise InconsistentCellError()
        _optional_count(self.branco)
        _optional_count(self.nulo)
        if self.comparecimento <= 0 or self.valid <= 0:
            raise InconsistentCellError()

    @property
    def valid(self) -> int:
        return sum(self.votes)

    def shares(self) -> tuple[Fraction, ...]:
        party = tuple(Fraction(vote, self.valid) for vote in self.votes)
        if self.branco is None or self.nulo is None:
            return party
        turnout = (
            Fraction(self.branco, self.comparecimento),
            Fraction(self.nulo, self.comparecimento),
        )
        return party + turnout

    def features(self) -> tuple[float, ...]:
        return tuple(float(share) for share in self.shares())


@dataclass(frozen=True, slots=True)
class ProfileDataset:
    cargo: str
    parties: tuple[int, ...]
    places: tuple[ProfilePlace, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "cargo", require_profile_cargo(self.cargo))
        if len(self.places) < _MIN_PLACES or not self.parties:
            raise FewMunicipalitiesError()
        width = len(self.parties)
        if any(len(place.votes) != width for place in self.places):
            raise InconsistentCellError()
        self._ballot()

    @property
    def with_ballot(self) -> bool:
        return self.cargo in _BALLOT_CARGOS

    def matrix(self) -> tuple[tuple[float, ...], ...]:
        return tuple(place.features() for place in self.places)

    def _ballot(self) -> None:
        informed = tuple(place.branco is not None for place in self.places)
        if self.with_ballot and not all(informed):
            raise InconsistentCellError()
        if not self.with_ballot and any(informed):
            raise InconsistentCellError()


@dataclass(frozen=True, slots=True)
class ProfileGroup:
    numero: int
    municipios: int
    comparecimento: int
    center: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ProfileCity:
    codigo: str
    nome: str
    grupo: int


@dataclass(frozen=True, slots=True)
class ProfileReport:
    ano: int
    turno: int
    cargo: str
    parties: tuple[int, ...]
    with_ballot: bool
    searched: bool
    silhouette: float | None
    groups: tuple[ProfileGroup, ...]
    cities: tuple[ProfileCity, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ano", ElectionYear(self.ano).value)
        object.__setattr__(self, "turno", Turno(self.turno).value)
        object.__setattr__(self, "cargo", require_profile_cargo(self.cargo))
        if not self.groups:
            raise FewMunicipalitiesError()

    @property
    def k(self) -> int:
        return len(self.groups)


def require_profile_cargo(cargo: object) -> str:
    if not isinstance(cargo, str):
        raise InvalidCargoError(cargo)
    text = cargo.strip()
    sentence = _DEPUTY_TEXT.get(text)
    if sentence is not None:
        raise CargoSemCelulasError(sentence)
    if text not in _PROFILE_CARGOS:
        raise InvalidCargoError(text)
    return text


def parse_group_span(text: str) -> GroupSpan:
    raw = text.strip()
    if raw == "":
        raise InvalidGroupSpanError()
    if "-" not in raw:
        chosen = _k(raw)
        return GroupSpan(chosen, chosen, False)
    return _span(raw)


def winning_k(scores: tuple[tuple[int, float], ...]) -> int:
    if not scores:
        raise InvalidGroupSpanError()
    best_k, best_score = scores[0]
    for k, score in scores[1:]:
        best_k, best_score = _prefer(best_k, best_score, k, score)
    return best_k


def dataset_from_lines(cargo: str, lines: tuple[ProfileLine, ...]) -> ProfileDataset:
    checked = require_profile_cargo(cargo)
    if not lines:
        raise EmptyStoredCellsError()
    kept = _kept(_fold(lines), checked)
    if len(kept) < _MIN_PLACES:
        raise FewMunicipalitiesError()
    parties = _parties(kept)
    places = tuple(_place(draft, parties, checked) for draft in kept)
    return ProfileDataset(checked, parties, places)


def assemble_profile(
    ano: int,
    turno: int,
    dataset: ProfileDataset,
    assignments: tuple[int, ...],
    centers: tuple[tuple[float, ...], ...],
    *,
    searched: bool,
    silhouette: float | None,
) -> ProfileReport:
    _require_fit(dataset, assignments, centers)
    ranked = tuple(sorted(_buckets(dataset, assignments, centers), key=lambda item: item.key))
    groups = tuple(_group(numero, item) for numero, item in enumerate(ranked, start=1))
    labels = _labels(ranked)
    return ProfileReport(
        ano,
        turno,
        dataset.cargo,
        dataset.parties,
        dataset.with_ballot,
        searched,
        silhouette,
        groups,
        _cities(dataset.places, labels),
    )


class _Draft:
    def __init__(self, line: ProfileLine) -> None:
        self.codigo = line.codigo
        self.nome = line.nome
        self.comparecimento = line.comparecimento
        self.votes: dict[int, int] = {}
        self.branco: int | None = None
        self.nulo: int | None = None
        self._vote(line)
        self._ballot(line)

    @property
    def valid(self) -> int:
        return sum(self.votes.values())

    def accept(self, line: ProfileLine) -> None:
        if line.nome != self.nome or line.comparecimento != self.comparecimento:
            raise InconsistentCellError()
        self._vote(line)
        self._ballot(line)

    def _vote(self, line: ProfileLine) -> None:
        total = line.votos_nominais + line.votos_legenda
        previous = self.votes.get(line.partido)
        if previous is not None and previous != total:
            raise InconsistentCellError()
        if previous is None:
            self.votes[line.partido] = total

    def _ballot(self, line: ProfileLine) -> None:
        if line.branco is None and line.nulo is None:
            return
        if line.branco is None or line.nulo is None:
            raise InconsistentCellError()
        if self.branco is None:
            self.branco = line.branco
            self.nulo = line.nulo
            return
        if self.branco != line.branco or self.nulo != line.nulo:
            raise InconsistentCellError()


def _fold(lines: tuple[ProfileLine, ...]) -> dict[str, _Draft]:
    found: dict[str, _Draft] = {}
    for line in lines:
        draft = found.get(line.codigo)
        if draft is None:
            found[line.codigo] = _Draft(line)
            continue
        draft.accept(line)
    return found


def _kept(found: dict[str, _Draft], cargo: str) -> tuple[_Draft, ...]:
    ordered = [found[codigo] for codigo in sorted(found)]
    return tuple(draft for draft in ordered if _eligible(draft, cargo))


def _eligible(draft: _Draft, cargo: str) -> bool:
    if draft.valid <= 0 or draft.comparecimento <= 0:
        return False
    missing_ballot = draft.branco is None or draft.nulo is None
    return not (cargo in _BALLOT_CARGOS and missing_ballot)


def _parties(drafts: tuple[_Draft, ...]) -> tuple[int, ...]:
    numbers: set[int] = set()
    for draft in drafts:
        numbers.update(draft.votes)
    if not numbers:
        raise FewMunicipalitiesError()
    return tuple(sorted(numbers))


def _place(draft: _Draft, parties: tuple[int, ...], cargo: str) -> ProfilePlace:
    votes = tuple(draft.votes.get(party, 0) for party in parties)
    branco = draft.branco if cargo in _BALLOT_CARGOS else None
    nulo = draft.nulo if cargo in _BALLOT_CARGOS else None
    return ProfilePlace(draft.codigo, draft.nome, draft.comparecimento, votes, branco, nulo)


@dataclass(frozen=True, slots=True)
class _Bucket:
    raw: int
    center: tuple[float, ...]
    members: tuple[ProfilePlace, ...]
    dominant: int

    @property
    def key(self) -> tuple[int, int, int, int]:
        turnout = sum(place.comparecimento for place in self.members)
        return (-len(self.members), -turnout, self.dominant, self.raw)


def _require_fit(
    dataset: ProfileDataset,
    assignments: tuple[int, ...],
    centers: tuple[tuple[float, ...], ...],
) -> None:
    if len(assignments) != len(dataset.places) or not centers:
        raise InconsistentCellError()
    width = len(dataset.places[0].shares())
    if any(len(center) != width for center in centers):
        raise InconsistentCellError()
    if any(label < 0 or label >= len(centers) for label in assignments):
        raise InconsistentCellError()


def _buckets(
    dataset: ProfileDataset,
    assignments: tuple[int, ...],
    centers: tuple[tuple[float, ...], ...],
) -> tuple[_Bucket, ...]:
    found: list[_Bucket] = []
    for raw, center in enumerate(centers):
        members = tuple(
            place for place, label in zip(dataset.places, assignments, strict=True) if label == raw
        )
        found.append(_Bucket(raw, center, members, _dominant(center, dataset.parties)))
    return tuple(found)


def _dominant(center: tuple[float, ...], parties: tuple[int, ...]) -> int:
    shares = center[: len(parties)]
    best = max(shares)
    winners = [party for party, share in zip(parties, shares, strict=True) if share == best]
    return min(winners)


def _group(numero: int, bucket: _Bucket) -> ProfileGroup:
    turnout = sum(place.comparecimento for place in bucket.members)
    return ProfileGroup(numero, len(bucket.members), turnout, bucket.center)


def _labels(ranked: tuple[_Bucket, ...]) -> dict[str, int]:
    labels: dict[str, int] = {}
    for numero, bucket in enumerate(ranked, start=1):
        for place in bucket.members:
            labels[place.codigo] = numero
    return labels


def _cities(places: tuple[ProfilePlace, ...], labels: dict[str, int]) -> tuple[ProfileCity, ...]:
    ordered = sorted(places, key=lambda place: _city_key(place, labels))
    return tuple(ProfileCity(place.codigo, place.nome, labels[place.codigo]) for place in ordered)


def _city_key(place: ProfilePlace, labels: dict[str, int]) -> tuple[int, str, str]:
    nome, codigo = place_sort_key(place.nome, place.codigo)
    return (labels[place.codigo], nome, codigo)


def _prefer(best_k: int, best_score: float, k: int, score: float) -> tuple[int, float]:
    if score > best_score:
        return k, score
    if score < best_score or k >= best_k:
        return best_k, best_score
    return k, score


def _span(raw: str) -> GroupSpan:
    parts = raw.split("-")
    if len(parts) != 2:
        raise InvalidGroupSpanError()
    return GroupSpan(_k(parts[0]), _k(parts[1]), True)


def _k(raw: str) -> int:
    text = raw.strip()
    if not (text.isascii() and text.isdecimal()):
        raise InvalidGroupSpanError()
    return int(text)


def _text(value: object) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise InconsistentCellError()
    return value.strip()


def _count(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InconsistentCellError()


def _optional_count(value: int | None) -> None:
    if value is not None:
        _count(value)


def _votes(votes: tuple[int, ...]) -> None:
    for vote in votes:
        _count(vote)


def _party(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InconsistentCellError()
    if value < 0 or value > _MAX_PARTY:
        raise InconsistentCellError()
