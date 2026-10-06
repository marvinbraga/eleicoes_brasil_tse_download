"""Party-share grid. Each cell computes votos / comparecimento; the ratio is not stored."""

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.boletim_consulta import PoderPartido, require_cargo
from eleicoes.domain.errors import InvalidBoletimConsultaError, InvalidNivelError
from eleicoes.domain.values import ElectionYear, Turno, Uf

_MAX_PARTIDO: Final = 99
_LEVELS: Final = frozenset({"municipio", "uf", "regiao", "pais"})


@dataclass(frozen=True, slots=True)
class GradeLevel:
    value: str

    def __post_init__(self) -> None:
        if self.value not in _LEVELS:
            raise InvalidNivelError(self.value)


@dataclass(frozen=True, slots=True)
class LugarVotos:
    codigo: str
    nome: str
    linhas: tuple[PoderPartido, ...]

    def __post_init__(self) -> None:
        _require_text(self.codigo, "codigo")
        _require_text(self.nome, "nome")
        if not self.linhas:
            raise InvalidBoletimConsultaError("linhas")
        turnout = self.linhas[0].comparecimento
        if any(line.comparecimento != turnout for line in self.linhas):
            raise InvalidBoletimConsultaError("comparecimento")
        object.__setattr__(self, "codigo", self.codigo.strip())
        object.__setattr__(self, "nome", self.nome.strip())

    @property
    def comparecimento(self) -> int:
        return self.linhas[0].comparecimento


@dataclass(frozen=True, slots=True)
class CelulaGrade:
    partido: int
    votos_nominais: int
    votos_legenda: int
    comparecimento: int

    def __post_init__(self) -> None:
        _require_range(self.partido, 0, _MAX_PARTIDO, "partido")
        _require_count(self.votos_nominais, "votos_nominais")
        _require_count(self.votos_legenda, "votos_legenda")
        _require_count(self.comparecimento, "comparecimento")

    @property
    def votos(self) -> int:
        return self.votos_nominais + self.votos_legenda

    @property
    def fatia(self) -> Fraction:
        if self.comparecimento == 0:
            return Fraction(0)
        return Fraction(self.votos, self.comparecimento)


@dataclass(frozen=True, slots=True)
class LinhaGrade:
    codigo: str
    nome: str
    comparecimento: int
    celulas: tuple[CelulaGrade, ...]

    def __post_init__(self) -> None:
        _require_text(self.codigo, "codigo")
        _require_text(self.nome, "nome")
        _require_count(self.comparecimento, "comparecimento")
        if any(cell.comparecimento != self.comparecimento for cell in self.celulas):
            raise InvalidBoletimConsultaError("comparecimento")
        parties = tuple(cell.partido for cell in self.celulas)
        if len(parties) != len(set(parties)):
            raise InvalidBoletimConsultaError("partido")
        object.__setattr__(self, "codigo", self.codigo.strip())
        object.__setattr__(self, "nome", self.nome.strip())


@dataclass(frozen=True, slots=True)
class GradeDePoder:
    ano: int
    turno: int
    uf: str
    cargo: str
    nivel: str
    colunas: tuple[int, ...]
    linhas: tuple[LinhaGrade, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ano", ElectionYear(self.ano).value)
        object.__setattr__(self, "turno", Turno(self.turno).value)
        object.__setattr__(self, "uf", Uf(self.uf).code)
        object.__setattr__(self, "cargo", require_cargo(self.cargo))
        object.__setattr__(self, "nivel", GradeLevel(self.nivel).value)
        _require_shape(self.colunas, self.linhas)


def ordered_parties(totals: Mapping[int, int]) -> tuple[int, ...]:
    return tuple(sorted(totals, key=lambda party: (-totals[party], party)))


def place_sort_key(nome: str, codigo: str) -> tuple[str, str]:
    return (nome.casefold(), codigo)


def _require_shape(colunas: tuple[int, ...], linhas: tuple[LinhaGrade, ...]) -> None:
    if len(colunas) != len(set(colunas)):
        raise InvalidBoletimConsultaError("partido")
    if colunas != ordered_parties(_cell_totals(linhas)):
        raise InvalidBoletimConsultaError("partido")
    _require_rows(colunas, linhas)


def _require_rows(colunas: tuple[int, ...], linhas: tuple[LinhaGrade, ...]) -> None:
    codes: set[str] = set()
    for linha in linhas:
        parties = tuple(cell.partido for cell in linha.celulas)
        if parties != colunas:
            raise InvalidBoletimConsultaError("partido")
        if linha.codigo in codes:
            raise InvalidBoletimConsultaError("codigo")
        codes.add(linha.codigo)
    keys = tuple(place_sort_key(linha.nome, linha.codigo) for linha in linhas)
    if keys != tuple(sorted(keys)):
        raise InvalidBoletimConsultaError("nome")


def _cell_totals(linhas: tuple[LinhaGrade, ...]) -> dict[int, int]:
    totals: dict[int, int] = {}
    for linha in linhas:
        for cell in linha.celulas:
            totals[cell.partido] = totals.get(cell.partido, 0) + cell.votos
    return totals


def _require_text(value: str, field: str) -> None:
    if not isinstance(value, str) or value.strip() == "":
        raise InvalidBoletimConsultaError(field)


def _require_count(value: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidBoletimConsultaError(field)


def _require_range(value: int, lower: int, upper: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidBoletimConsultaError(field)
    if value < lower or value > upper:
        raise InvalidBoletimConsultaError(field)
