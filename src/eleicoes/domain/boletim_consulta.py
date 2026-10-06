"""Frozen records for boletim consultations. They do not read the database."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, TypeAlias

from eleicoes.domain.correspondencia.indicio import Gravidade
from eleicoes.domain.errors import (
    InvalidBoletimConsultaError,
    InvalidCargoError,
    InvalidNivelError,
    InvalidNumeroError,
    InvalidOrdemError,
)
from eleicoes.domain.regiao import REGION_NAMES, region_of
from eleicoes.domain.values import UF_CODES, Uf

_MAX_MUNICIPIO: Final = 99999
_MAX_ZONA: Final = 9999
_MAX_SECAO: Final = 9999
_MAX_NUMERO: Final = 99999
_MAX_PARTIDO: Final = 99
_MAX_ORDEM: Final = 99
_ORDERS: Final = frozenset({"mais", "menos"})
_LEVELS: Final = frozenset({"municipio", "zona", "secao"})
_PLACE_LEVELS: Final = frozenset({"municipio", "zona"})
_LEGEND: Final = "legenda"
_NOMINAL: Final = "nominal"
_UNIT_DIVISOR: Final = 1
_TEN_DIVISOR: Final = 10
_HUNDRED_DIVISOR: Final = 100
_THOUSAND_DIVISOR: Final = 1_000
_SENATOR_MIN: Final = 100
_SENATOR_MAX: Final = 999
_FEDERAL_MIN: Final = 1_000
_FEDERAL_MAX: Final = 9_999
_STATE_MIN: Final = 10_000
_UNNUMBERED: Final = frozenset({"branco", "nulo"})
_NUMBERED: Final = frozenset({_NOMINAL, _LEGEND})
_VOTE_KINDS: Final = frozenset({*_UNNUMBERED, *_NUMBERED, "cargoSemCandidato"})
_Width: TypeAlias = tuple[int, int, int]
_LEGEND_WIDTHS: Final[tuple[_Width, ...]] = ((0, _MAX_PARTIDO, _UNIT_DIVISOR),)
_NOMINAL_WIDTHS: Final[tuple[_Width, ...]] = (
    (0, _MAX_PARTIDO, _UNIT_DIVISOR),
    (_SENATOR_MIN, _SENATOR_MAX, _TEN_DIVISOR),
    (_FEDERAL_MIN, _FEDERAL_MAX, _HUNDRED_DIVISOR),
    (_STATE_MIN, _MAX_NUMERO, _THOUSAND_DIVISOR),
)
_PARTY_WIDTHS: Final[dict[str, tuple[_Width, ...]]] = {
    _LEGEND: _LEGEND_WIDTHS,
    _NOMINAL: _NOMINAL_WIDTHS,
}


@dataclass(frozen=True, slots=True)
class RankingOrder:
    value: str

    def __post_init__(self) -> None:
        if self.value not in _ORDERS:
            raise InvalidOrdemError(self.value)


@dataclass(frozen=True, slots=True)
class ComparisonLevel:
    value: str

    def __post_init__(self) -> None:
        if self.value not in _LEVELS:
            raise InvalidNivelError(self.value)


@dataclass(frozen=True, slots=True)
class PlaceLevel:
    value: str

    def __post_init__(self) -> None:
        if self.value not in _PLACE_LEVELS:
            raise InvalidNivelError(self.value)


@dataclass(frozen=True, slots=True)
class PartyScope:
    ufs: tuple[str, ...]
    regiao: str | None = None

    def __post_init__(self) -> None:
        if len(self.ufs) == 0:
            raise InvalidBoletimConsultaError("uf")
        normalized = tuple(Uf(code).code for code in self.ufs)
        if len(set(normalized)) != len(normalized):
            raise InvalidBoletimConsultaError("uf")
        object.__setattr__(self, "ufs", normalized)
        _require_region_name(self.regiao)


def _single_state(uf: str) -> PartyScope:
    return PartyScope((Uf(uf).code,))


def _macro_region(uf: str) -> PartyScope:
    region = region_of(uf)
    return PartyScope(region.ufs, region.name)


def _whole_country(uf: str) -> PartyScope:
    Uf(uf)
    return PartyScope(UF_CODES)


_ScopeRule: TypeAlias = Callable[[str], PartyScope]
_SCOPE_RULES: Final[dict[str, _ScopeRule]] = {
    "municipio": _single_state,
    "zona": _single_state,
    "uf": _single_state,
    "regiao": _macro_region,
    "pais": _whole_country,
}


@dataclass(frozen=True, slots=True)
class PartyLevel:
    value: str

    def __post_init__(self) -> None:
        if self.value not in _SCOPE_RULES:
            raise InvalidNivelError(self.value)

    def scope(self, uf: str) -> PartyScope:
        return _SCOPE_RULES[self.value](uf)


@dataclass(frozen=True, slots=True)
class TotalCargo:
    tipo_voto: str
    partido: int | None
    numero: int | None
    quantidade: int

    def __post_init__(self) -> None:
        _require_identity(self.tipo_voto, self.partido, self.numero)
        _require_count(self.quantidade, "quantidade")


@dataclass(frozen=True, slots=True)
class VotosMunicipio:
    municipio: int
    quantidade: int
    comparecimento: int

    def __post_init__(self) -> None:
        _require_range(self.municipio, 1, _MAX_MUNICIPIO, "municipio")
        _require_count(self.quantidade, "quantidade")
        _require_count(self.comparecimento, "comparecimento")


@dataclass(frozen=True, slots=True)
class Comparativo:
    municipio: int
    zona: int | None
    secao: int | None
    votos_primeiro: int
    votos_segundo: int
    comparecimento: int

    def __post_init__(self) -> None:
        _require_range(self.municipio, 1, _MAX_MUNICIPIO, "municipio")
        _require_section(self.zona, self.secao)
        _require_count(self.votos_primeiro, "votos_primeiro")
        _require_count(self.votos_segundo, "votos_segundo")
        _require_count(self.comparecimento, "comparecimento")


@dataclass(frozen=True, slots=True)
class PoderPartido:
    municipio: int | None
    zona: int | None
    partido: int
    votos_nominais: int
    votos_legenda: int
    comparecimento: int
    regiao: str | None = None

    def __post_init__(self) -> None:
        _require_party_place(self.municipio, self.zona)
        _require_range(self.partido, 0, _MAX_PARTIDO, "partido")
        _require_count(self.votos_nominais, "votos_nominais")
        _require_count(self.votos_legenda, "votos_legenda")
        _require_count(self.comparecimento, "comparecimento")
        _require_region_name(self.regiao)

    @property
    def votos(self) -> int:
        return self.votos_nominais + self.votos_legenda


@dataclass(frozen=True, slots=True)
class Participacao:
    municipio: int
    zona: int | None
    eleitores_aptos: int
    comparecimento: int

    def __post_init__(self) -> None:
        _require_range(self.municipio, 1, _MAX_MUNICIPIO, "municipio")
        _require_optional_zone(self.zona)
        _require_count(self.eleitores_aptos, "eleitores_aptos")
        _require_count(self.comparecimento, "comparecimento")
        if self.comparecimento > self.eleitores_aptos:
            raise InvalidBoletimConsultaError("comparecimento")

    @property
    def abstencao(self) -> int:
        return self.eleitores_aptos - self.comparecimento


@dataclass(frozen=True, slots=True)
class BrancosNulos:
    municipio: int
    zona: int | None
    branco: int
    nulo: int
    comparecimento: int

    def __post_init__(self) -> None:
        _require_range(self.municipio, 1, _MAX_MUNICIPIO, "municipio")
        _require_optional_zone(self.zona)
        _require_count(self.branco, "branco")
        _require_count(self.nulo, "nulo")
        _require_count(self.comparecimento, "comparecimento")

    @property
    def votos(self) -> int:
        return self.branco + self.nulo


@dataclass(frozen=True, slots=True)
class PrimeiroColocado:
    municipio: int
    zona: int | None
    numero: int
    partido: int
    votos: int
    segundo_numero: int | None
    segundo_partido: int | None
    segundo_votos: int | None
    comparecimento: int

    def __post_init__(self) -> None:
        _require_range(self.municipio, 1, _MAX_MUNICIPIO, "municipio")
        _require_optional_zone(self.zona)
        _require_range(self.numero, 0, _MAX_NUMERO, "numero")
        _require_range(self.partido, 0, _MAX_PARTIDO, "partido")
        _require_count(self.votos, "votos")
        _require_runner_up(self.segundo_numero, self.segundo_partido, self.segundo_votos)
        _require_count(self.comparecimento, "comparecimento")


@dataclass(frozen=True, slots=True)
class LinhaVoto:
    cargo: str
    ordem_impressao: int
    tipo_voto: str
    partido: int | None
    numero: int | None
    quantidade: int

    def __post_init__(self) -> None:
        _require_text(self.cargo, "cargo")
        _require_range(self.ordem_impressao, 1, _MAX_ORDEM, "ordem_impressao")
        _require_identity(self.tipo_voto, self.partido, self.numero)
        _require_count(self.quantidade, "quantidade")


@dataclass(frozen=True, slots=True)
class VotosZona:
    zona: int
    quantidade: int
    comparecimento: int

    def __post_init__(self) -> None:
        _require_range(self.zona, 1, _MAX_ZONA, "zona")
        _require_count(self.quantidade, "quantidade")
        _require_count(self.comparecimento, "comparecimento")


@dataclass(frozen=True, slots=True)
class IndicioBoletim:
    codigo: str
    descricao: str
    gravidade: Gravidade
    uf: str
    municipio: int
    zona: int | None
    secao: int | None
    medida: str

    def __post_init__(self) -> None:
        _require_text(self.codigo, "codigo")
        _require_text(self.descricao, "descricao")
        _require_text(self.medida, "medida")
        if not isinstance(self.gravidade, Gravidade):
            raise InvalidBoletimConsultaError("gravidade")
        if not isinstance(self.uf, str):
            raise InvalidBoletimConsultaError("uf")
        object.__setattr__(self, "uf", Uf(self.uf).code)
        _require_range(self.municipio, 1, _MAX_MUNICIPIO, "municipio")
        _require_section(self.zona, self.secao)


@dataclass(frozen=True, slots=True)
class SectionProjection:
    municipio: int
    zona: int
    secao: int
    comparecimento: int
    quantidade: int

    def __post_init__(self) -> None:
        _require_range(self.municipio, 1, _MAX_MUNICIPIO, "municipio")
        _require_range(self.zona, 1, _MAX_ZONA, "zona")
        _require_range(self.secao, 1, _MAX_SECAO, "secao")
        _require_count(self.comparecimento, "comparecimento")
        _require_count(self.quantidade, "quantidade")


@dataclass(frozen=True, slots=True)
class NominalProjection:
    municipio: int
    numero: int
    quantidade: int

    def __post_init__(self) -> None:
        _require_range(self.municipio, 1, _MAX_MUNICIPIO, "municipio")
        _require_range(self.numero, 0, _MAX_NUMERO, "numero")
        _require_count(self.quantidade, "quantidade")


@dataclass(frozen=True, slots=True)
class BlankNullProjection:
    municipio: int
    quantidade: int

    def __post_init__(self) -> None:
        _require_range(self.municipio, 1, _MAX_MUNICIPIO, "municipio")
        _require_count(self.quantidade, "quantidade")


def require_cargo(cargo: str) -> str:
    if not isinstance(cargo, str) or cargo.strip() == "":
        raise InvalidCargoError(cargo)
    return cargo


def require_numero(numero: int) -> int:
    if isinstance(numero, bool) or not isinstance(numero, int):
        raise InvalidNumeroError(numero)
    if numero < 0 or numero > _MAX_NUMERO:
        raise InvalidNumeroError(numero)
    return numero


def require_municipio(municipio: int) -> int:
    _require_range(municipio, 1, _MAX_MUNICIPIO, "municipio")
    return municipio


def require_zona(zona: int) -> int:
    _require_range(zona, 1, _MAX_ZONA, "zona")
    return zona


def require_secao(secao: int) -> int:
    _require_range(secao, 1, _MAX_SECAO, "secao")
    return secao


# Candidatos a presidente em 2026. A urna grava qualquer número digitado como
# voto nominal; a totalização do TSE conta número sem candidato como nulo.
_PRESIDENTIAL_CANDIDATES: Final = frozenset(
    {13, 14, 16, 21, 22, 27, 29, 30, 35, 55, 70, 80}
)


def partido_tem_candidato(cargo: str, partido: int) -> bool:
    if cargo != "presidente":
        return True
    return partido in _PRESIDENTIAL_CANDIDATES


def partido_do_numero(tipo_voto: str, numero: int) -> int:
    if isinstance(numero, bool) or not isinstance(numero, int):
        raise InvalidNumeroError(numero)
    widths = _PARTY_WIDTHS.get(tipo_voto)
    if widths is None:
        raise InvalidNumeroError(tipo_voto)
    return _party_from_widths(numero, widths)


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


def _require_optional_zone(zona: int | None) -> None:
    if zona is not None:
        _require_range(zona, 1, _MAX_ZONA, "zona")


def _require_party_place(municipio: int | None, zona: int | None) -> None:
    if municipio is None:
        if zona is not None:
            raise InvalidBoletimConsultaError("zona")
        return
    _require_range(municipio, 1, _MAX_MUNICIPIO, "municipio")
    _require_optional_zone(zona)


def _require_region_name(regiao: str | None) -> None:
    if regiao is not None and regiao not in REGION_NAMES:
        raise InvalidBoletimConsultaError("regiao")


def _require_runner_up(
    numero: int | None,
    partido: int | None,
    votos: int | None,
) -> None:
    if numero is None and partido is None and votos is None:
        return
    if numero is None or partido is None or votos is None:
        raise InvalidBoletimConsultaError("segundo")
    _require_range(numero, 0, _MAX_NUMERO, "segundo_numero")
    _require_range(partido, 0, _MAX_PARTIDO, "segundo_partido")
    _require_count(votos, "segundo_votos")


def _party_from_widths(numero: int, widths: tuple[_Width, ...]) -> int:
    for lower, upper, divisor in widths:
        if lower <= numero <= upper:
            return numero // divisor
    raise InvalidNumeroError(numero)


def _require_section(zona: int | None, secao: int | None) -> None:
    if secao is not None and zona is None:
        raise InvalidBoletimConsultaError("secao")
    if zona is not None:
        _require_range(zona, 1, _MAX_ZONA, "zona")
    if secao is not None:
        _require_range(secao, 1, _MAX_SECAO, "secao")


def _require_identity(tipo_voto: str, partido: int | None, numero: int | None) -> None:
    if tipo_voto not in _VOTE_KINDS:
        raise InvalidBoletimConsultaError("tipo_voto")
    _require_pair(tipo_voto, partido, numero)


def _require_pair(tipo_voto: str, partido: int | None, numero: int | None) -> None:
    present = partido is not None or numero is not None
    complete = partido is not None and numero is not None
    _require_complete(tipo_voto, present, complete)
    if partido is not None:
        _require_range(partido, 0, _MAX_PARTIDO, "partido")
    if numero is not None:
        _require_range(numero, 0, _MAX_NUMERO, "numero")


def _require_complete(tipo_voto: str, present: bool, complete: bool) -> None:
    if tipo_voto in _UNNUMBERED and present:
        raise InvalidBoletimConsultaError("identificacao")
    if tipo_voto in _NUMBERED and not complete:
        raise InvalidBoletimConsultaError("identificacao")
    if present and not complete:
        raise InvalidBoletimConsultaError("identificacao")
