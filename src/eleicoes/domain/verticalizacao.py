"""Party strength across offices, read from the stored power cells. No ballot is read."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Final

from eleicoes.domain.errors import InconsistentCellError, InvalidUfError, MissingPowerReportError
from eleicoes.domain.values import UF_CODES, ElectionYear, Turno

PRESIDENTE: Final = "presidente"
GOVERNADOR: Final = "governador"
SENADOR: Final = "senador"
DEPUTADO_FEDERAL: Final = "deputadoFederal"
DEPUTADO_ESTADUAL: Final = "deputadoEstadual"
CARGOS: Final[tuple[str, ...]] = (
    PRESIDENTE,
    GOVERNADOR,
    SENADOR,
    DEPUTADO_FEDERAL,
    DEPUTADO_ESTADUAL,
)
MAJORITARIOS: Final[tuple[str, ...]] = (PRESIDENTE, GOVERNADOR, SENADOR)
PROPORCIONAIS: Final[tuple[str, ...]] = (DEPUTADO_FEDERAL, DEPUTADO_ESTADUAL)
EXTERIOR: Final = "ZZ"
_MUNICIPIO: Final = "municipio"
_UF: Final = "uf"
MAX_PARTIDO: Final = 99
_SUFIXO: Final = re.compile(r"\(([A-Z]{2})\)\s*$")
_STATES: Final = frozenset(UF_CODES) - {EXTERIOR}

Votes = Mapping[int, int]


@dataclass(frozen=True, slots=True)
class VerticalLine:
    cargo: str
    nivel: str
    codigo: str
    nome: str
    comparecimento: int
    partido: int
    votos: int

    def __post_init__(self) -> None:
        if self.cargo not in CARGOS or self.nivel not in (_MUNICIPIO, _UF):
            raise InconsistentCellError()
        object.__setattr__(self, "codigo", _text(self.codigo))
        object.__setattr__(self, "nome", _text(self.nome))
        _count(self.comparecimento)
        _count(self.votos)
        _count(self.partido)
        if self.partido > MAX_PARTIDO:
            raise InconsistentCellError()


@dataclass(frozen=True, slots=True, eq=False)
class MunicipioVertical:
    codigo: str
    nome: str
    uf: str
    comparecimento: int
    votos: Mapping[str, Votes]
    validos: Mapping[str, int]


@dataclass(frozen=True, slots=True, eq=False)
class VerticalBase:
    ano: int
    turno: int
    estados: Mapping[str, Mapping[str, Votes]]
    municipios: Mapping[str, tuple[MunicipioVertical, ...]]
    sem_uf: int

    def scope(self, uf: str | None) -> tuple[str, ...]:
        if uf is None:
            return tuple(sorted(self.estados))
        code = uf.strip().upper()
        if code not in self.estados:
            raise InvalidUfError(uf)
        return (code,)

    def votos_uf(self, uf: str, cargo: str) -> Votes:
        return self.estados.get(uf, {}).get(cargo, {})

    def validos_uf(self, uf: str, cargo: str) -> int:
        return sum(self.votos_uf(uf, cargo).values())

    def concorreu(self, uf: str, cargo: str, partido: int) -> bool:
        return self.votos_uf(uf, cargo).get(partido, 0) > 0


@dataclass(frozen=True, slots=True)
class CargoShare:
    cargo: str
    votos: int
    validos: int
    validos_onde: int
    ufs_concorreu: int
    ufs_total: int

    @property
    def fatia(self) -> Fraction | None:
        if self.validos == 0:
            return None
        return Fraction(self.votos, self.validos)

    @property
    def fatia_onde(self) -> Fraction | None:
        if self.ufs_concorreu == 0 or self.validos_onde == 0:
            return None
        return Fraction(self.votos, self.validos_onde)


@dataclass(slots=True)
class _CityDraft:
    nome: str
    comparecimento: int
    votos: dict[str, dict[int, int]] = field(default_factory=dict)


def municipal_uf(nome: str) -> str | None:
    found = _SUFIXO.search(nome)
    if found is None:
        return None
    code = found.group(1)
    if code in _STATES or code == EXTERIOR:
        return code
    return None


def vertical_base(ano: int, turno: int, lines: tuple[VerticalLine, ...]) -> VerticalBase:
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    states: dict[str, dict[str, dict[int, int]]] = {}
    cities: dict[str, _CityDraft] = {}
    for line in lines:
        if line.votos == 0:
            continue
        if line.nivel == _UF:
            _put_state(states, line)
        else:
            _put_city(cities, line)
    _require_cargos(states)
    grouped, orphans = _group_cities(cities)
    return VerticalBase(year, turn, states, grouped, orphans)


def cargo_share(base: VerticalBase, ufs: tuple[str, ...], cargo: str, partido: int) -> CargoShare:
    votos = validos = onde = concorreu = total = 0
    for uf in ufs:
        valid = base.validos_uf(uf, cargo)
        if valid == 0:
            continue
        total += 1
        validos += valid
        own = base.votos_uf(uf, cargo).get(partido, 0)
        if own > 0:
            votos += own
            onde += valid
            concorreu += 1
    return CargoShare(cargo, votos, validos, onde, concorreu, total)


def _put_state(states: dict[str, dict[str, dict[int, int]]], line: VerticalLine) -> None:
    if line.codigo == EXTERIOR:
        return
    if line.codigo not in _STATES:
        raise InconsistentCellError()
    by_cargo = states.setdefault(line.codigo, {}).setdefault(line.cargo, {})
    by_cargo[line.partido] = by_cargo.get(line.partido, 0) + line.votos


def _put_city(cities: dict[str, _CityDraft], line: VerticalLine) -> None:
    draft = cities.get(line.codigo)
    if draft is None:
        draft = _CityDraft(line.nome, line.comparecimento)
        cities[line.codigo] = draft
    draft.comparecimento = max(draft.comparecimento, line.comparecimento)
    by_cargo = draft.votos.setdefault(line.cargo, {})
    by_cargo[line.partido] = by_cargo.get(line.partido, 0) + line.votos


def _require_cargos(states: Mapping[str, Mapping[str, Votes]]) -> None:
    present = {cargo for by_cargo in states.values() for cargo in by_cargo}
    for cargo in CARGOS:
        if cargo not in present:
            raise MissingPowerReportError(cargo)


def _group_cities(
    cities: Mapping[str, _CityDraft],
) -> tuple[dict[str, tuple[MunicipioVertical, ...]], int]:
    grouped: dict[str, list[MunicipioVertical]] = {}
    orphans = 0
    for codigo, draft in cities.items():
        uf = municipal_uf(draft.nome)
        if uf is None:
            orphans += 1
            continue
        if uf == EXTERIOR:
            continue
        validos = {cargo: sum(votes.values()) for cargo, votes in draft.votos.items()}
        city = MunicipioVertical(codigo, draft.nome, uf, draft.comparecimento, draft.votos, validos)
        grouped.setdefault(uf, []).append(city)
    ordered = {
        uf: tuple(sorted(items, key=lambda city: (city.nome.casefold(), city.codigo)))
        for uf, items in grouped.items()
    }
    return ordered, orphans


def _text(value: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise InconsistentCellError()
    return value.strip()


def _count(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InconsistentCellError()
