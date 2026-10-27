"""Regiões e porte dos municípios: o 1º × 2º turno de presidente por grupo.

Só entram os municípios gravados nos dois turnos. A é o finalista de referência
(o 13, se chegou ao 2º turno) e B o outro. As fatias do 2º turno são sobre os
válidos; a virada é a mudança na fatia de A entre os votos dos dois finalistas.
O porte é o eleitorado apto do 1º turno; o exterior não tem porte e só entra
nas regiões.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.mapa_turnos import chave_tse, finalistas
from eleicoes.domain.presidente_governador import MunicipalPlace
from eleicoes.domain.regiao import REGIONS, region_of
from eleicoes.domain.values import UF_CODES, ElectionYear

REFERENCIA: Final = 13
EXTERIOR: Final = "ZZ"
_EXTERIOR_NOME: Final = "Exterior"
_BRASIL: Final = "BR"
_BRASIL_NOME: Final = "Brasil"
_ZERO: Final = Fraction(0)


@dataclass(frozen=True, slots=True)
class FaixaDePorte:
    """Municípios com até ``ate`` eleitores aptos; a última faixa não tem teto."""

    chave: str
    rotulo: str
    ate: int | None

    def __post_init__(self) -> None:
        if self.ate is not None and self.ate <= 0:
            raise InvalidBoletimConsultaError("porte")


FAIXAS_DE_PORTE: Final[tuple[FaixaDePorte, ...]] = (
    FaixaDePorte("ate_10_mil", "Até 10 mil eleitores", 10_000),
    FaixaDePorte("10_a_50_mil", "De 10 mil a 50 mil", 50_000),
    FaixaDePorte("50_a_200_mil", "De 50 mil a 200 mil", 200_000),
    FaixaDePorte("200_mil_a_1_milhao", "De 200 mil a 1 milhão", 1_000_000),
    FaixaDePorte("acima_de_1_milhao", "Acima de 1 milhão", None),
)


def faixa_de_porte(
    eleitores: int, faixas: tuple[FaixaDePorte, ...] = FAIXAS_DE_PORTE
) -> FaixaDePorte:
    """10.000 aptos ainda é "até 10 mil"; 10.001 já é a faixa seguinte."""
    if eleitores < 0:
        raise InvalidBoletimConsultaError("eleitores_aptos")
    for faixa in faixas:
        if faixa.ate is None or eleitores <= faixa.ate:
            return faixa
    raise InvalidBoletimConsultaError("porte")


@dataclass(frozen=True, slots=True)
class VotosTurno:
    a: int
    b: int
    validos: int

    def __post_init__(self) -> None:
        for campo, valor in (("a", self.a), ("b", self.b), ("validos", self.validos)):
            if valor < 0:
                raise InvalidBoletimConsultaError(campo)
        if self.a + self.b > self.validos:
            raise InvalidBoletimConsultaError("validos")

    @property
    def fatia_a(self) -> Fraction:
        return _fatia(self.a, self.validos)

    @property
    def fatia_b(self) -> Fraction:
        return _fatia(self.b, self.validos)

    @property
    def fatia_a_no_par(self) -> Fraction:
        """Fatia de A só entre os votos dos dois finalistas."""
        return _fatia(self.a, self.a + self.b)

    def __add__(self, outro: "VotosTurno") -> "VotosTurno":
        return VotosTurno(self.a + outro.a, self.b + outro.b, self.validos + outro.validos)


_VAZIO: Final = VotosTurno(0, 0, 0)


@dataclass(frozen=True, slots=True)
class LinhaGrupo:
    chave: str
    rotulo: str
    municipios: int
    primeiro: VotosTurno
    segundo: VotosTurno

    @property
    def diferenca(self) -> int:
        """Votos de A menos votos de B no 2º turno."""
        return self.segundo.a - self.segundo.b

    @property
    def variacao_a(self) -> int:
        return self.segundo.a - self.primeiro.a

    @property
    def variacao_b(self) -> int:
        return self.segundo.b - self.primeiro.b

    @property
    def variacao_relativa_a(self) -> Fraction | None:
        return _relativa(self.variacao_a, self.primeiro.a)

    @property
    def variacao_relativa_b(self) -> Fraction | None:
        return _relativa(self.variacao_b, self.primeiro.b)

    @property
    def virada(self) -> Fraction:
        """Mudança da fatia de A entre os dois finalistas, do 1º para o 2º turno."""
        return self.segundo.fatia_a_no_par - self.primeiro.fatia_a_no_par


@dataclass(frozen=True, slots=True)
class RegioesEPorte:
    ano: int
    a: int
    b: int
    regioes: tuple[LinhaGrupo, ...]
    portes: tuple[LinhaGrupo, ...]
    brasil: LinhaGrupo
    brasil_sem_exterior: LinhaGrupo
    sem_segundo_turno: tuple[str, ...]
    fora_do_relatorio: tuple[str, ...]
    so_no_primeiro: int
    so_no_segundo: int
    sem_eleitorado: int


def parte_do_ganho_de_a(linha: LinhaGrupo, total: LinhaGrupo) -> Fraction | None:
    """Quanto da variação de votos de A no total veio do grupo."""
    return _relativa(linha.variacao_a, total.variacao_a)


def ufs_com_os_dois_turnos(
    primeiro: Sequence[MunicipalPlace], segundo: Sequence[MunicipalPlace]
) -> tuple[str, ...]:
    """UFs com municípios gravados nos dois turnos, na ordem oficial, sem o exterior."""
    antes = {place.uf for place in primeiro}
    depois = {place.uf for place in segundo}
    return tuple(uf for uf in UF_CODES if uf != EXTERIOR and uf in antes and uf in depois)


def regioes_e_porte(
    ano: int,
    primeiro: Sequence[MunicipalPlace],
    segundo: Sequence[MunicipalPlace],
    eleitores: Mapping[tuple[str, str], int],
    *,
    referencia: int = REFERENCIA,
    ufs_no_boletim: Sequence[str] = (),
) -> RegioesEPorte:
    """``eleitores`` usa a chave (UF, código TSE de cinco dígitos), como o mapa.

    ``ufs_no_boletim`` são as UFs que já têm 2º turno nos boletins; as que faltam
    nos lugares gravados aparecem em ``fora_do_relatorio``.
    """
    year = ElectionYear(ano).value
    a, b = finalistas(segundo, referencia)
    antes = {(place.uf, place.codigo): place for place in primeiro}
    depois = {(place.uf, place.codigo): place for place in segundo}
    pares = [(antes[chave], place) for chave, place in depois.items() if chave in antes]
    ufs_depois = {uf for uf, _ in depois}
    regioes: dict[str, _Soma] = {}
    portes: dict[str, _Soma] = {faixa.chave: _Soma() for faixa in FAIXAS_DE_PORTE}
    brasil = _Soma()
    sem_exterior = _Soma()
    sem_eleitorado = 0
    for anterior, atual in pares:
        votos = (_votos(anterior, a, b), _votos(atual, a, b))
        brasil.somar(*votos)
        regioes.setdefault(_regiao(atual.uf), _Soma()).somar(*votos)
        if atual.uf == EXTERIOR:
            continue
        sem_exterior.somar(*votos)
        aptos = eleitores.get((atual.uf, chave_tse(atual.codigo)))
        if aptos is None:
            sem_eleitorado += 1
            continue
        portes[faixa_de_porte(aptos).chave].somar(*votos)
    return RegioesEPorte(
        ano=year,
        a=a,
        b=b,
        regioes=tuple(
            regioes[nome].linha(nome, nome) for nome in _ORDEM_DAS_REGIOES if nome in regioes
        ),
        portes=tuple(
            portes[faixa.chave].linha(faixa.chave, faixa.rotulo) for faixa in FAIXAS_DE_PORTE
        ),
        brasil=brasil.linha(_BRASIL, _BRASIL_NOME),
        brasil_sem_exterior=sem_exterior.linha(_BRASIL, _BRASIL_NOME),
        sem_segundo_turno=tuple(uf for uf in UF_CODES if uf not in ufs_depois),
        fora_do_relatorio=tuple(
            uf for uf in UF_CODES if uf in ufs_no_boletim and uf not in ufs_depois
        ),
        so_no_primeiro=sum(1 for chave in antes if chave[0] in ufs_depois and chave not in depois),
        so_no_segundo=sum(1 for chave in depois if chave not in antes),
        sem_eleitorado=sem_eleitorado,
    )


_ORDEM_DAS_REGIOES: Final[tuple[str, ...]] = (
    *(region.name for region in REGIONS),
    _EXTERIOR_NOME,
)


class _Soma:
    def __init__(self) -> None:
        self.municipios = 0
        self.primeiro = _VAZIO
        self.segundo = _VAZIO

    def somar(self, primeiro: VotosTurno, segundo: VotosTurno) -> None:
        self.municipios += 1
        self.primeiro = self.primeiro + primeiro
        self.segundo = self.segundo + segundo

    def linha(self, chave: str, rotulo: str) -> LinhaGrupo:
        return LinhaGrupo(chave, rotulo, self.municipios, self.primeiro, self.segundo)


def _regiao(uf: str) -> str:
    if uf == EXTERIOR:
        return _EXTERIOR_NOME
    return region_of(uf).name


def _votos(place: MunicipalPlace, a: int, b: int) -> VotosTurno:
    votos = {party.partido: party.votos for party in place.presidente.parties}
    return VotosTurno(votos.get(a, 0), votos.get(b, 0), place.presidente.valid)


def _fatia(votos: int, total: int) -> Fraction:
    if total == 0:
        return _ZERO
    return Fraction(votos, total)


def _relativa(variacao: int, base: int) -> Fraction | None:
    if base == 0:
        return None
    return Fraction(variacao, base)
