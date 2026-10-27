"""De onde vieram os votos novos dos finalistas entre o 1º e o 2º turno de presidente.

Num município, as cédulas de cada turno se dividem entre os finalistas A e B,
os eliminados O (zero no 2º turno) e branco + nulo BN. O comparecimento C, lido
no boletim, deveria ser igual às cédulas. Subtraindo um turno do outro:

    ΔA + ΔB = O₁ − O₂ − ΔBN + Δcédulas

Com O₂ = 0 e cédulas = comparecimento, sobra a identidade do relatório:

    ΔA + ΔB = O₁ − ΔBN + ΔC

Os votos novos dos finalistas vêm de três fontes: os votos dos eliminados, os
brancos e nulos que viraram voto válido (−ΔBN) e o comparecimento a mais (ΔC).
O resíduo ΔA + ΔB − (O₁ − ΔBN + ΔC) é, pela mesma conta,

    (cédulas₂ − C₂) − (cédulas₁ − C₁) − O₂

e só deixa de ser zero quando as cédulas gravadas não batem com o comparecimento
num turno ou quando o 2º turno tem voto fora dos finalistas: problema de dado,
como uma UF ainda carregando, nunca de comportamento do eleitor.

As correlações são ecológicas: descrevem municípios, não eleitores.
"""

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Final

from eleicoes.domain.mapa_turnos import chave_tse, finalistas
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace
from eleicoes.domain.regiao import region_of
from eleicoes.domain.values import UF_CODES

MINIMO_DE_FINALISTAS: Final = 1000
TAMANHO_DO_TOPO: Final = 20
EXTERIOR: Final = "ZZ"
REGIAO_EXTERIOR: Final = "Exterior"
_PONTOS_PERCENTUAIS: Final = 100

# (turno, UF, código TSE de cinco dígitos) → (aptos, comparecimento) de presidente.
Participacoes = Mapping[tuple[int, str, str], tuple[int, int]]


@dataclass(frozen=True, slots=True)
class VotosDoTurno:
    """Votos de presidente num turno, separados entre os finalistas A e B."""

    a: int
    b: int
    outros: int
    branco_nulo: int
    aptos: int
    comparecimento: int

    @property
    def finalistas(self) -> int:
        return self.a + self.b

    @property
    def validos(self) -> int:
        return self.a + self.b + self.outros

    @property
    def cedulas(self) -> int:
        return self.validos + self.branco_nulo

    @property
    def sobra(self) -> int:
        """Cédulas gravadas menos comparecimento do boletim. Deveria ser zero."""
        return self.cedulas - self.comparecimento

    @property
    def parte_de_a(self) -> Fraction | None:
        if self.finalistas == 0:
            return None
        return Fraction(self.a, self.finalistas)

    def __add__(self, other: "VotosDoTurno") -> "VotosDoTurno":
        return VotosDoTurno(
            self.a + other.a,
            self.b + other.b,
            self.outros + other.outros,
            self.branco_nulo + other.branco_nulo,
            self.aptos + other.aptos,
            self.comparecimento + other.comparecimento,
        )


_ZERO: Final = VotosDoTurno(0, 0, 0, 0, 0, 0)


@dataclass(frozen=True, slots=True)
class Balanco:
    """Os dois turnos de um lugar e as contas da origem dos votos novos."""

    primeiro: VotosDoTurno
    segundo: VotosDoTurno

    @property
    def delta_a(self) -> int:
        return self.segundo.a - self.primeiro.a

    @property
    def delta_b(self) -> int:
        return self.segundo.b - self.primeiro.b

    @property
    def novos(self) -> int:
        """ΔA + ΔB: votos que os finalistas somaram do 1º para o 2º turno."""
        return self.delta_a + self.delta_b

    @property
    def eliminados(self) -> int:
        """O₁: votos dos eliminados no 1º turno."""
        return self.primeiro.outros

    @property
    def delta_branco_nulo(self) -> int:
        return self.segundo.branco_nulo - self.primeiro.branco_nulo

    @property
    def brancos_nulos_liberados(self) -> int:
        """−ΔBN: brancos e nulos a menos no 2º turno entram como fonte positiva."""
        return -self.delta_branco_nulo

    @property
    def delta_comparecimento(self) -> int:
        return self.segundo.comparecimento - self.primeiro.comparecimento

    @property
    def delta_aptos(self) -> int:
        return self.segundo.aptos - self.primeiro.aptos

    @property
    def fontes(self) -> int:
        """O₁ − ΔBN + ΔC, o lado direito da identidade."""
        return self.eliminados + self.brancos_nulos_liberados + self.delta_comparecimento

    @property
    def residuo(self) -> int:
        """ΔA + ΔB − (O₁ − ΔBN + ΔC) = sobra₂ − sobra₁ − O₂. Zero quando o dado fecha."""
        return self.novos - self.fontes

    @property
    def fecha(self) -> bool:
        return self.residuo == 0

    @property
    def virada(self) -> Fraction | None:
        """Variação da fatia de A entre os finalistas, do 1º para o 2º turno, em fração."""
        antes = self.primeiro.parte_de_a
        depois = self.segundo.parte_de_a
        if antes is None or depois is None:
            return None
        return depois - antes

    def __add__(self, other: "Balanco") -> "Balanco":
        return Balanco(self.primeiro + other.primeiro, self.segundo + other.segundo)


@dataclass(frozen=True, slots=True)
class MunicipioOrigem:
    uf: str
    codigo: str
    nome: str
    balanco: Balanco

    @property
    def regiao(self) -> str:
        if self.uf == EXTERIOR:
            return REGIAO_EXTERIOR
        return region_of(self.uf).name


@dataclass(frozen=True, slots=True)
class UfOrigem:
    uf: str
    municipios: int
    falhas: int
    balanco: Balanco


@dataclass(frozen=True, slots=True)
class Ponto:
    x: float
    y: float
    peso: int
    uf: str
    nome: str
    regiao: str


@dataclass(frozen=True, slots=True)
class Dispersao:
    """Um ponto por município, com reta e correlações ponderadas pelas cédulas do 1º turno."""

    pontos: tuple[Ponto, ...]
    pearson: float | None
    spearman: float | None
    inclinacao: float | None
    intercepto: float | None


@dataclass(frozen=True, slots=True)
class LugarAusente:
    uf: str
    codigo: str
    nome: str


@dataclass(frozen=True, slots=True)
class OrigemDosVotos:
    a: int
    b: int
    municipios: tuple[MunicipioOrigem, ...]
    total: Balanco
    ufs: tuple[UfOrigem, ...]
    por_comparecimento: Dispersao
    por_eliminados: Dispersao
    topo_a: tuple[MunicipioOrigem, ...]
    topo_b: tuple[MunicipioOrigem, ...]
    so_no_primeiro: tuple[LugarAusente, ...]
    so_no_segundo: tuple[LugarAusente, ...]
    sem_comparecimento: tuple[LugarAusente, ...]
    ufs_sem_segundo_turno: tuple[str, ...] = field(default=())

    @property
    def falhas(self) -> tuple[MunicipioOrigem, ...]:
        return tuple(municipio for municipio in self.municipios if not municipio.balanco.fecha)


def analisar_origem(
    primeiro: Sequence[MunicipalPlace],
    segundo: Sequence[MunicipalPlace],
    participacoes: Participacoes,
    *,
    minimo: int = MINIMO_DE_FINALISTAS,
    topo: int = TAMANHO_DO_TOPO,
) -> OrigemDosVotos:
    """Cruza os dois turnos por município. Só entra o município com os dois turnos e o
    comparecimento dos dois; os demais vão para as listas de ausentes."""
    a, b = sorted(finalistas(segundo))
    antes = _por_chave(primeiro)
    depois = _por_chave(segundo)
    municipios: list[MunicipioOrigem] = []
    sem_comparecimento: list[LugarAusente] = []
    for chave, place in depois.items():
        anterior = antes.get(chave)
        if anterior is None:
            continue
        uf, codigo = chave
        lido_1 = participacoes.get((1, uf, codigo))
        lido_2 = participacoes.get((2, uf, codigo))
        if lido_1 is None or lido_2 is None:
            sem_comparecimento.append(LugarAusente(uf, codigo, place.nome))
            continue
        balanco = Balanco(
            _turno(anterior.presidente, a, b, lido_1), _turno(place.presidente, a, b, lido_2)
        )
        municipios.append(MunicipioOrigem(uf, codigo, place.nome, balanco))
    municipios.sort(key=_ordem)
    ufs_do_segundo = {uf for uf, _ in depois}
    return OrigemDosVotos(
        a=a,
        b=b,
        municipios=tuple(municipios),
        total=_somar(municipios),
        ufs=_por_uf(municipios),
        por_comparecimento=dispersao(municipios, _x_comparecimento),
        por_eliminados=dispersao(municipios, _x_eliminados),
        topo_a=_topo(municipios, minimo, topo, para_a=True),
        topo_b=_topo(municipios, minimo, topo, para_a=False),
        so_no_primeiro=_ausentes(antes, depois, ufs_do_segundo),
        so_no_segundo=_ausentes(depois, antes, None),
        sem_comparecimento=tuple(sorted(sem_comparecimento, key=_ordem)),
        ufs_sem_segundo_turno=tuple(
            uf for uf in UF_CODES if uf in {u for u, _ in antes} and uf not in ufs_do_segundo
        ),
    )


def dispersao(
    municipios: Sequence[MunicipioOrigem],
    eixo_x: Callable[[Balanco], float | None],
) -> Dispersao:
    pontos: list[Ponto] = []
    for municipio in municipios:
        balanco = municipio.balanco
        x = eixo_x(balanco)
        virada = balanco.virada
        peso = balanco.primeiro.cedulas
        if x is None or virada is None or peso == 0:
            continue
        y = float(virada) * _PONTOS_PERCENTUAIS
        pontos.append(Ponto(x, y, peso, municipio.uf, municipio.nome, municipio.regiao))
    xs = [ponto.x for ponto in pontos]
    ys = [ponto.y for ponto in pontos]
    pesos = [float(ponto.peso) for ponto in pontos]
    reta = reta_ponderada(xs, ys, pesos)
    return Dispersao(
        tuple(pontos),
        pearson_ponderado(xs, ys, pesos),
        spearman_ponderado(xs, ys, pesos),
        None if reta is None else reta[1],
        None if reta is None else reta[0],
    )


def reta_ponderada(
    xs: Sequence[float], ys: Sequence[float], pesos: Sequence[float]
) -> tuple[float, float] | None:
    """(intercepto, inclinação) dos mínimos quadrados ponderados. None sem variação em x."""
    momentos = _momentos(xs, ys, pesos)
    if momentos is None:
        return None
    media_x, media_y, var_x, _, cov = momentos
    if var_x <= 0:
        return None
    inclinacao = cov / var_x
    return media_y - inclinacao * media_x, inclinacao


def pearson_ponderado(
    xs: Sequence[float], ys: Sequence[float], pesos: Sequence[float]
) -> float | None:
    momentos = _momentos(xs, ys, pesos)
    if momentos is None:
        return None
    _, _, var_x, var_y, cov = momentos
    if var_x <= 0 or var_y <= 0:
        return None
    return cov / math.sqrt(var_x * var_y)


def spearman_ponderado(
    xs: Sequence[float], ys: Sequence[float], pesos: Sequence[float]
) -> float | None:
    """Pearson ponderado das posições. A posição de cada valor é o peso acumulado até o
    meio do seu grupo de empate, então um município grande ocupa uma faixa larga."""
    if len(xs) < 2:
        return None
    return pearson_ponderado(_posicoes(xs, pesos), _posicoes(ys, pesos), pesos)


def _momentos(
    xs: Sequence[float], ys: Sequence[float], pesos: Sequence[float]
) -> tuple[float, float, float, float, float] | None:
    total = math.fsum(pesos)
    if len(xs) < 2 or total <= 0:
        return None
    media_x = math.fsum(w * x for x, w in zip(xs, pesos, strict=True)) / total
    media_y = math.fsum(w * y for y, w in zip(ys, pesos, strict=True)) / total
    var_x = math.fsum(w * (x - media_x) ** 2 for x, w in zip(xs, pesos, strict=True)) / total
    var_y = math.fsum(w * (y - media_y) ** 2 for y, w in zip(ys, pesos, strict=True)) / total
    cov = (
        math.fsum(w * (x - media_x) * (y - media_y) for x, y, w in zip(xs, ys, pesos, strict=True))
        / total
    )
    return media_x, media_y, var_x, var_y, cov


def _posicoes(valores: Sequence[float], pesos: Sequence[float]) -> list[float]:
    ordem = sorted(range(len(valores)), key=lambda indice: valores[indice])
    posicoes = [0.0] * len(valores)
    acumulado = 0.0
    inicio = 0
    while inicio < len(ordem):
        fim = inicio
        while fim + 1 < len(ordem) and valores[ordem[fim + 1]] == valores[ordem[inicio]]:
            fim += 1
        grupo = ordem[inicio : fim + 1]
        peso = math.fsum(pesos[indice] for indice in grupo)
        for indice in grupo:
            posicoes[indice] = acumulado + peso / 2
        acumulado += peso
        inicio = fim + 1
    return posicoes


def _x_comparecimento(balanco: Balanco) -> float | None:
    """ΔC em % das cédulas do 1º turno."""
    cedulas = balanco.primeiro.cedulas
    if cedulas == 0:
        return None
    return balanco.delta_comparecimento / cedulas * _PONTOS_PERCENTUAIS


def _x_eliminados(balanco: Balanco) -> float | None:
    """Fatia dos eliminados nos votos válidos do 1º turno, em %."""
    validos = balanco.primeiro.validos
    if validos == 0:
        return None
    return balanco.eliminados / validos * _PONTOS_PERCENTUAIS


def _turno(tally: CargoTally, a: int, b: int, lido: tuple[int, int]) -> VotosDoTurno:
    votos = {party.partido: party.votos for party in tally.parties}
    outros = sum(total for numero, total in votos.items() if numero not in (a, b))
    aptos, comparecimento = lido
    return VotosDoTurno(
        votos.get(a, 0),
        votos.get(b, 0),
        outros,
        tally.branco + tally.nulo,
        aptos,
        comparecimento,
    )


def _por_chave(places: Sequence[MunicipalPlace]) -> dict[tuple[str, str], MunicipalPlace]:
    return {(place.uf, chave_tse(place.codigo)): place for place in places}


def _somar(municipios: Sequence[MunicipioOrigem]) -> Balanco:
    total = Balanco(_ZERO, _ZERO)
    for municipio in municipios:
        total = total + municipio.balanco
    return total


def _por_uf(municipios: Sequence[MunicipioOrigem]) -> tuple[UfOrigem, ...]:
    grupos: dict[str, list[MunicipioOrigem]] = {}
    for municipio in municipios:
        grupos.setdefault(municipio.uf, []).append(municipio)
    return tuple(
        UfOrigem(
            uf,
            len(grupos[uf]),
            sum(1 for municipio in grupos[uf] if not municipio.balanco.fecha),
            _somar(grupos[uf]),
        )
        for uf in UF_CODES
        if uf in grupos
    )


def _topo(
    municipios: Sequence[MunicipioOrigem], minimo: int, tamanho: int, *, para_a: bool
) -> tuple[MunicipioOrigem, ...]:
    """Maiores viradas para A (ou B) entre os municípios com ao menos `minimo` votos de
    finalista em cada turno."""
    candidatos = [
        municipio
        for municipio in municipios
        if municipio.balanco.virada is not None
        and municipio.balanco.primeiro.finalistas >= minimo
        and municipio.balanco.segundo.finalistas >= minimo
    ]
    sinal = -1 if para_a else 1
    candidatos.sort(key=lambda municipio: (sinal * _virada(municipio), _ordem(municipio)))
    return tuple(candidatos[:tamanho])


def _virada(municipio: MunicipioOrigem) -> Fraction:
    virada = municipio.balanco.virada
    return Fraction(0) if virada is None else virada


def _ausentes(
    de: Mapping[tuple[str, str], MunicipalPlace],
    em: Mapping[tuple[str, str], MunicipalPlace],
    ufs: set[str] | None,
) -> tuple[LugarAusente, ...]:
    """Lugares de `de` sem par em `em`. Com `ufs`, só os das UFs que têm o outro turno:
    uma UF inteira ausente aparece à parte."""
    found = [
        LugarAusente(uf, codigo, place.nome)
        for (uf, codigo), place in de.items()
        if (uf, codigo) not in em and (ufs is None or uf in ufs)
    ]
    return tuple(sorted(found, key=_ordem))


def _ordem(lugar: MunicipioOrigem | LugarAusente) -> tuple[int, str, str]:
    posicao = UF_CODES.index(lugar.uf) if lugar.uf in UF_CODES else len(UF_CODES)
    return posicao, lugar.nome, lugar.codigo
