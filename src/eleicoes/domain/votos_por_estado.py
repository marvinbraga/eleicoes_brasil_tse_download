"""Como votou cada estado: os dois mais votados do país, UF por UF.

As fatias são sobre todos os votos válidos de presidente da UF. No 2º turno os
válidos são só dos dois finalistas; no 1º, os demais candidatos ficam no
denominador e somem do gráfico. A cobertura conta as seções com boletim de
urna baixado sobre as seções que o índice de download espera no turno.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.errors import ElectionError
from eleicoes.domain.mapa_turnos import finalistas
from eleicoes.domain.percentual import format_integer, round_half_up
from eleicoes.domain.presidente_governador import MunicipalPlace
from eleicoes.domain.values import UF_CODES, ElectionYear, Turno, uf_name

REFERENCIA: Final = 13
EXTERIOR: Final = "ZZ"
ESTADOS: Final[tuple[str, ...]] = tuple(uf for uf in UF_CODES if uf != EXTERIOR)
_PAIS: Final = "BR"
_PAIS_NOME: Final = "Brasil"
_ZERO: Final = Fraction(0)
_UM: Final = Fraction(1)
_BASE: Final = 1
_MIL: Final = 1000
_MILHAO: Final = 1_000_000


class StatesMissingError(ElectionError):
    def __init__(self, ano: int, turno: int) -> None:
        self.ano = ano
        self.turno = turno
        super().__init__(f"no stored president votes for {ano}, round {turno}")


class InvalidCoverageError(ElectionError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"invalid urn coverage: {field}")


@dataclass(frozen=True, slots=True)
class SecoesIndice:
    """Seções de uma UF num turno do índice de download: listadas e com boletim baixado."""

    listadas: int
    com_boletim: int

    def __post_init__(self) -> None:
        if self.listadas < 0:
            raise InvalidCoverageError("listadas")
        if not 0 <= self.com_boletim <= self.listadas:
            raise InvalidCoverageError("com_boletim")


# (turno, UF) → seções do índice.
ContagemIndice = Mapping[tuple[int, str], SecoesIndice]


@dataclass(frozen=True, slots=True)
class Cobertura:
    """Seções com boletim baixado e, se o índice souber, as esperadas no turno."""

    com_boletim: int
    esperadas: int | None

    def __post_init__(self) -> None:
        if self.com_boletim < 0:
            raise InvalidCoverageError("com_boletim")
        if self.esperadas is not None and self.esperadas < 0:
            raise InvalidCoverageError("esperadas")

    @property
    def fatia(self) -> Fraction | None:
        if not self.esperadas:
            return None
        return Fraction(self.com_boletim, self.esperadas)


@dataclass(frozen=True, slots=True)
class CoberturaUrnas:
    """`base` é o turno cujas seções listadas dão as esperadas; None se o índice não serve."""

    total: Cobertura
    por_uf: Mapping[str, Cobertura]
    base: int | None


def cobertura_do_turno(contagem: ContagemIndice, turno: int) -> CoberturaUrnas:
    """O índice só lista as seções que o TSE já publicou no turno. No 2º turno ainda em
    curso faltam UFs inteiras, então as esperadas vêm do 1º turno: a eleição de
    presidente usa as mesmas seções nos dois turnos. Sem 1º turno no índice, as
    esperadas ficam desconhecidas."""
    round_ = Turno(turno).value
    com_boletim = {uf: secoes.com_boletim for (t, uf), secoes in contagem.items() if t == round_}
    base = {uf: secoes.listadas for (t, uf), secoes in contagem.items() if t == _BASE}
    if not base:
        soltas = {uf: Cobertura(n, None) for uf, n in com_boletim.items()}
        return CoberturaUrnas(Cobertura(sum(com_boletim.values()), None), soltas, None)
    ufs = sorted(set(base) | set(com_boletim))
    por_uf = {uf: Cobertura(com_boletim.get(uf, 0), base.get(uf)) for uf in ufs}
    total = Cobertura(sum(com_boletim.values()), sum(base.values()))
    return CoberturaUrnas(total, por_uf, _BASE)


@dataclass(frozen=True, slots=True)
class LinhaEstado:
    uf: str
    nome: str
    votos_a: int
    votos_b: int
    validos: int

    @property
    def fatia_a(self) -> Fraction:
        return _fatia(self.votos_a, self.validos)

    @property
    def fatia_b(self) -> Fraction:
        return _fatia(self.votos_b, self.validos)

    @property
    def diferenca(self) -> int:
        """Votos que separam os dois, sempre a favor de quem venceu."""
        return abs(self.votos_a - self.votos_b)

    def vencedor(self, a: int, b: int) -> int | None:
        if self.votos_a == self.votos_b:
            return None
        return a if self.votos_a > self.votos_b else b


@dataclass(frozen=True, slots=True)
class VotosPorEstado:
    ano: int
    turno: int
    a: int
    b: int
    estados: tuple[LinhaEstado, ...]
    exterior: LinhaEstado | None
    brasil: LinhaEstado
    faltando: tuple[str, ...]
    cobertura: CoberturaUrnas

    @property
    def vitorias_a(self) -> int:
        return sum(1 for linha in self.estados if linha.vencedor(self.a, self.b) == self.a)

    @property
    def vitorias_b(self) -> int:
        return sum(1 for linha in self.estados if linha.vencedor(self.a, self.b) == self.b)

    def parcial(self, uf: str) -> Fraction | None:
        """Fatia das urnas da UF com boletim baixado, quando o índice mostra que falta alguma."""
        cobertura = self.cobertura.por_uf.get(uf)
        fatia = None if cobertura is None else cobertura.fatia
        if fatia is None or fatia >= _UM:
            return None
        return fatia

    @property
    def demais_omitidos(self) -> bool:
        """No 1º turno os outros candidatos ficam fora das barras."""
        return self.brasil.votos_a + self.brasil.votos_b < self.brasil.validos


def votos_por_estado(
    ano: int,
    turno: int,
    places: Sequence[MunicipalPlace],
    cobertura: CoberturaUrnas,
    referencia: int = REFERENCIA,
) -> VotosPorEstado:
    """Ordena as UFs pela fatia de A, decrescente; A é a referência se ela for finalista."""
    year = ElectionYear(ano).value
    round_ = Turno(turno).value
    if not places:
        raise StatesMissingError(year, round_)
    a, b = finalistas(places, referencia)
    linhas = {uf: _linha(uf, uf_name(uf), grupo, a, b) for uf, grupo in _por_uf(places).items()}
    estados = tuple(
        sorted(
            (linha for uf, linha in linhas.items() if uf != EXTERIOR),
            key=lambda linha: (-linha.fatia_a, -linha.votos_a, linha.uf),
        )
    )
    return VotosPorEstado(
        ano=year,
        turno=round_,
        a=a,
        b=b,
        estados=estados,
        exterior=linhas.get(EXTERIOR),
        brasil=_linha(_PAIS, _PAIS_NOME, places, a, b),
        faltando=tuple(uf for uf in ESTADOS if uf not in linhas),
        cobertura=cobertura,
    )


def _por_uf(places: Sequence[MunicipalPlace]) -> dict[str, list[MunicipalPlace]]:
    grupos: dict[str, list[MunicipalPlace]] = {}
    for place in places:
        grupos.setdefault(place.uf, []).append(place)
    return grupos


def _linha(uf: str, nome: str, places: Sequence[MunicipalPlace], a: int, b: int) -> LinhaEstado:
    votos: dict[int, int] = {}
    validos = 0
    for place in places:
        for party in place.presidente.parties:
            votos[party.partido] = votos.get(party.partido, 0) + party.votos
            validos += party.votos
    return LinhaEstado(uf, nome, votos.get(a, 0), votos.get(b, 0), validos)


def _fatia(votos: int, validos: int) -> Fraction:
    if validos == 0:
        return _ZERO
    return Fraction(votos, validos)


def votos_compactos(votos: int) -> str:
    """1.130.000 → "1,13 mi"; 929.400 → "929 mil"; abaixo de mil, o número inteiro."""
    if votos < 0:
        raise InvalidCoverageError("votos")
    if votos < _MIL:
        return format_integer(votos)
    mil = round_half_up(Fraction(votos, _MIL))
    if mil < _MIL:
        return f"{mil} mil"
    centesimos = round_half_up(Fraction(votos, _MILHAO // 100))
    inteiro, resto = divmod(centesimos, 100)
    return f"{format_integer(inteiro)},{resto:02d} mi"
