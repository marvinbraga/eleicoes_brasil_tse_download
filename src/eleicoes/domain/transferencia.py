"""Transferência de votos do 1º para o 2º turno de presidente, estimada pelos dados.

Regressão ecológica de Goodman, uma por UF. Cada município i dá a fatia das
cédulas do 1º turno em cada grupo (x_ig) e a fatia das cédulas do 2º turno em
cada destino (y_ik). O modelo supõe uma taxa β_gk comum a todos os municípios
da UF:

    y_ik ≈ Σ_g x_ig · β_gk

Grupos do 1º turno: os dois finalistas (A e B), cada eliminado com pelo menos
1% dos votos válidos do país, os demais eliminados juntos ("outros") e
branco + nulo. Destinos do 2º turno: A, B e branco + nulo. Cada taxa fica em
[0, 1] e cada linha soma 1, de modo que β_g· diz para onde foi o eleitor do
grupo g. O ajuste é por mínimos quadrados ponderados pelas cédulas do 1º turno,
resolvido por gradiente projetado acelerado (FISTA) com projeção de cada linha
no simplex. O intervalo vem de bootstrap dos municípios, com semente fixa.

Suposições e limites:

- Fatias, não votos: o modelo compara a composição das cédulas de um turno com
  a do outro, então o tamanho do comparecimento se cancela. Quem votou num
  turno e faltou no outro, ou só votou no 2º, não entra no modelo; a conta age
  como se o mesmo eleitorado tivesse votado duas vezes.
- Falácia ecológica: a taxa descreve municípios, não pessoas. Muitas matrizes
  de eleitores diferentes produzem os mesmos totais municipais, e a regressão
  escolhe a que melhor explica a variação entre municípios. Se o eleitor de um
  grupo se comporta de jeitos diferentes conforme o lugar, a taxa média sai
  enviesada.
- Colinearidade: a taxa de um grupo só é identificada se a fatia dele varia
  entre municípios de um jeito que não se confunde com a dos outros grupos.
  Eliminados pequenos, ou com fatia quase constante na UF, dão taxas instáveis
  e intervalos largos; com poucos municípios (AC, AP) o problema piora.
- Não prova irregularidade: um ajuste ruim ou uma taxa inesperada só diz que
  esse modelo simples explica mal o voto. Abstenção diferente entre turnos,
  eleitor novo, apuração parcial e comportamento local explicam o mesmo.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

import numpy as np
import numpy.typing as npt

from eleicoes.domain.errors import ElectionError
from eleicoes.domain.mapa_turnos import apuracao, chave_tse
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace
from eleicoes.domain.values import UF_CODES

LIMIAR_DE_DESTAQUE: Final = Fraction(1, 100)
MINIMO_DE_MUNICIPIOS: Final = 12
AMOSTRA_PEQUENA: Final = 30
REAMOSTRAS: Final = 1000
NIVEL: Final = 0.9
SEMENTE: Final = 0
OUTROS: Final = "outros"
BRANCO_NULO: Final = "branco_nulo"
DESTINOS: Final = ("a", "b", BRANCO_NULO)
_EXTERIOR: Final = "ZZ"
_ITERACOES: Final = 20000
_TOLERANCIA: Final = 1e-10

_Matriz = npt.NDArray[np.float64]
_Vetor = npt.NDArray[np.float64]


class TooFewPlacesError(ElectionError):
    def __init__(self, uf: str, found: int, minimum: int) -> None:
        self.uf = uf
        self.found = found
        self.minimum = minimum
        super().__init__(f"{uf} has {found} comparable places, at least {minimum} are needed")


class InvalidConfidenceLevelError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"confidence level must be between 0 and 1: {value}")


class InvalidResampleCountError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"resample count must not be negative: {value}")


@dataclass(frozen=True, slots=True)
class Grupos:
    """Linhas da matriz: A, B, eliminados em destaque, outros, branco + nulo."""

    a: int
    b: int
    destacados: tuple[int, ...]

    @property
    def chaves(self) -> tuple[str, ...]:
        partidos = (self.a, self.b, *self.destacados)
        return (*(str(numero) for numero in partidos), OUTROS, BRANCO_NULO)

    @property
    def eliminados(self) -> tuple[int, ...]:
        """Índices das linhas dos eliminados: os destacados e os outros."""
        return tuple(range(2, 3 + len(self.destacados)))

    def contar(self, tally: CargoTally) -> tuple[int, ...]:
        votos = {party.partido: party.votos for party in tally.parties}
        nomeados = (self.a, self.b, *self.destacados)
        outros = sum(total for numero, total in votos.items() if numero not in nomeados)
        return (
            *(votos.get(numero, 0) for numero in nomeados),
            outros,
            tally.branco + tally.nulo,
        )


@dataclass(frozen=True, slots=True)
class Observacao:
    """Um município: votos do 1º turno por grupo e do 2º por destino."""

    uf: str
    codigo: str
    nome: str
    primeiro: tuple[int, ...]
    segundo: tuple[int, int, int]

    @property
    def cedulas_primeiro(self) -> int:
        return sum(self.primeiro)

    @property
    def cedulas_segundo(self) -> int:
        return sum(self.segundo)


@dataclass(frozen=True, slots=True)
class Taxa:
    estimada: float
    inferior: float
    superior: float


@dataclass(frozen=True, slots=True)
class LinhaDeTransferencia:
    """Para onde foram as cédulas de um grupo do 1º turno: A, B e branco + nulo."""

    grupo: str
    votos: int
    taxas: tuple[Taxa, Taxa, Taxa]


@dataclass(frozen=True, slots=True)
class EstimativaDeTransferencia:
    uf: str
    a: int
    b: int
    municipios: int
    linhas: tuple[LinhaDeTransferencia, ...]
    ausentes: tuple[str, ...]
    parte_de_a: Taxa
    r2_de_a: float
    rmse: float
    nivel: float
    reamostras: int

    @property
    def amostra_pequena(self) -> bool:
        return self.municipios < AMOSTRA_PEQUENA


def grupos_do_primeiro(
    primeiro: Sequence[MunicipalPlace],
    a: int,
    b: int,
    *,
    limiar: Fraction = LIMIAR_DE_DESTAQUE,
) -> Grupos:
    """Eliminados com pelo menos `limiar` dos votos válidos do 1º turno, do maior ao menor."""
    totais: dict[int, int] = {}
    for place in primeiro:
        for party in place.presidente.parties:
            totais[party.partido] = totais.get(party.partido, 0) + party.votos
    validos = sum(totais.values())
    destacados = tuple(
        numero
        for numero in sorted(totais, key=lambda numero: (-totais[numero], numero))
        if numero not in (a, b) and validos > 0 and Fraction(totais[numero], validos) >= limiar
    )
    return Grupos(a, b, destacados)


def observacoes(
    primeiro: Sequence[MunicipalPlace],
    segundo: Sequence[MunicipalPlace],
    grupos: Grupos,
) -> tuple[Observacao, ...]:
    """Municípios presentes nos dois turnos, fora o exterior, na ordem das UFs."""
    antes = {(place.uf, chave_tse(place.codigo)): place for place in primeiro}
    found: list[Observacao] = []
    for place in segundo:
        chave = (place.uf, chave_tse(place.codigo))
        anterior = antes.get(chave)
        if anterior is None or place.uf == _EXTERIOR:
            continue
        final = apuracao(place.presidente, grupos.a, grupos.b)
        found.append(
            Observacao(
                place.uf,
                chave[1],
                place.nome,
                grupos.contar(anterior.presidente),
                (final.a, final.b, final.branco + final.nulo),
            )
        )
    ordem = {code: indice for indice, code in enumerate(UF_CODES)}
    found.sort(key=lambda obs: (ordem.get(obs.uf, len(ordem)), obs.codigo))
    return tuple(found)


def estimar_por_uf(
    lista: Sequence[Observacao],
    grupos: Grupos,
    *,
    minimo: int = MINIMO_DE_MUNICIPIOS,
    reamostras: int = REAMOSTRAS,
    nivel: float = NIVEL,
    semente: int = SEMENTE,
) -> tuple[tuple[EstimativaDeTransferencia, ...], tuple[str, ...]]:
    """Estima cada UF com amostra suficiente. Devolve também as UFs puladas."""
    estimadas: list[EstimativaDeTransferencia] = []
    puladas: list[str] = []
    for uf in UF_CODES:
        grupo = tuple(obs for obs in lista if obs.uf == uf)
        if not grupo:
            continue
        try:
            estimadas.append(
                estimar_transferencia(
                    grupo,
                    grupos,
                    uf,
                    minimo=minimo,
                    reamostras=reamostras,
                    nivel=nivel,
                    semente=semente,
                )
            )
        except TooFewPlacesError:
            puladas.append(uf)
    return tuple(estimadas), tuple(puladas)


def estimar_transferencia(
    lista: Sequence[Observacao],
    grupos: Grupos,
    uf: str,
    *,
    minimo: int = MINIMO_DE_MUNICIPIOS,
    reamostras: int = REAMOSTRAS,
    nivel: float = NIVEL,
    semente: int = SEMENTE,
) -> EstimativaDeTransferencia:
    """Matriz de transferência de um conjunto de municípios, com intervalo por bootstrap."""
    if not 0 < nivel < 1:
        raise InvalidConfidenceLevelError(nivel)
    if reamostras < 0:
        raise InvalidResampleCountError(reamostras)
    usados = tuple(obs for obs in lista if obs.cedulas_primeiro > 0 and obs.cedulas_segundo > 0)
    if len(usados) < minimo:
        raise TooFewPlacesError(uf, len(usados), minimo)
    contas = np.array([obs.primeiro for obs in usados], dtype=np.float64)
    presentes = np.flatnonzero(contas.sum(axis=0) > 0)
    contas = contas[:, presentes]
    finais = np.array([obs.segundo for obs in usados], dtype=np.float64)
    pesos = contas.sum(axis=1)
    x = contas / pesos[:, None]
    y = finais / finais.sum(axis=1)[:, None]
    beta = ajustar(x, y, pesos)
    eliminados = _posicoes(grupos.eliminados, presentes)
    pontual = _parte(beta, contas.sum(axis=0), eliminados)
    amostras, partes = _bootstrap(x, y, contas, beta, eliminados, reamostras, semente)
    chaves = grupos.chaves
    com_votos = {int(indice) for indice in presentes}
    return EstimativaDeTransferencia(
        uf,
        grupos.a,
        grupos.b,
        len(usados),
        _linhas(beta, amostras, contas, presentes, chaves, nivel),
        tuple(chave for indice, chave in enumerate(chaves) if indice not in com_votos),
        _taxa(pontual, partes, nivel),
        _r2(x, y, pesos, beta),
        _rmse(x, y, pesos, beta),
        nivel,
        reamostras,
    )


def parte_estimada_de_a(estimativa: EstimativaDeTransferencia) -> Fraction:
    """Dos votos dos eliminados que foram para um finalista, a parte que foi para A.

    Pronta para `Cenario.parte_de_a` em `mapa_turnos`.
    """
    return Fraction(estimativa.parte_de_a.estimada).limit_denominator(10_000)


def ajustar(x: _Matriz, y: _Matriz, pesos: _Vetor) -> _Matriz:
    """Mínimos quadrados ponderados com cada linha de β no simplex.

    `x` é n × G (fatias do 1º turno), `y` é n × K (fatias do 2º), `pesos` tem n
    valores não negativos. Devolve β, G × K. Sem peso nenhum, devolve a divisão
    igual entre os destinos.
    """
    inicio = np.full((1, x.shape[1], y.shape[1]), 1.0 / y.shape[1])
    gram, cruzado = _normais(x, y, pesos[None, :])
    return np.asarray(_fista(gram, cruzado, inicio)[0], dtype=np.float64)


def projetar_no_simplex(linhas: _Matriz) -> _Matriz:
    """Projeção euclidiana de cada linha (último eixo) no simplex {v ≥ 0, Σ v = 1}.

    Algoritmo de Duchi et al. (2008).
    """
    planas = linhas.reshape(-1, linhas.shape[-1])
    largura = planas.shape[1]
    ordenadas = -np.sort(-planas, axis=1)
    acumuladas = np.cumsum(ordenadas, axis=1) - 1.0
    validas = ordenadas - acumuladas / np.arange(1, largura + 1) > 0
    ultimo = largura - 1 - np.argmax(validas[:, ::-1], axis=1)
    limiar = acumuladas[np.arange(planas.shape[0]), ultimo] / (ultimo + 1)
    projetadas = np.maximum(planas - limiar[:, None], 0.0)
    return np.asarray(projetadas.reshape(linhas.shape), dtype=np.float64)


def _normais(x: _Matriz, y: _Matriz, pesos: _Matriz) -> tuple[_Matriz, _Matriz]:
    """XᵀWX e XᵀWY de cada linha de `pesos` (R × n), com os pesos somando 1."""
    totais = pesos.sum(axis=1)
    normalizados = pesos / np.where(totais > 0, totais, 1.0)[:, None]
    gram = np.einsum("rn,ng,nh->rgh", normalizados, x, x)
    cruzado = np.einsum("rn,ng,nk->rgk", normalizados, x, y)
    return gram, cruzado


def _fista(gram: _Matriz, cruzado: _Matriz, inicio: _Matriz) -> _Matriz:
    """Gradiente projetado acelerado, com reinício adaptativo, em R problemas de uma vez."""
    lipschitz = np.linalg.eigvalsh(gram)[:, -1]
    passo = np.where(lipschitz > 0, 1.0 / np.where(lipschitz > 0, lipschitz, 1.0), 0.0)
    passo = passo[:, None, None]
    atual = inicio
    ponto = inicio
    momento = np.ones(gram.shape[0])
    for _ in range(_ITERACOES):
        proximo = projetar_no_simplex(ponto - passo * (gram @ ponto - cruzado))
        passo_dado = proximo - atual
        # Reinício: o momento passou a empurrar contra a descida.
        reinicia = np.einsum("rgk,rgk->r", ponto - proximo, passo_dado) > 0
        seguinte = np.where(reinicia, 1.0, (1.0 + np.sqrt(1.0 + 4.0 * momento * momento)) / 2.0)
        impulso = np.where(reinicia, 0.0, (momento - 1.0) / seguinte)
        ponto = proximo + impulso[:, None, None] * passo_dado
        atual = proximo
        momento = seguinte
        if float(np.abs(passo_dado).max()) < _TOLERANCIA:
            break
    return atual


def _bootstrap(
    x: _Matriz,
    y: _Matriz,
    contas: _Matriz,
    beta: _Matriz,
    eliminados: tuple[int, ...],
    reamostras: int,
    semente: int,
) -> tuple[_Matriz, _Vetor]:
    """Reamostra municípios com reposição. Cada réplica parte da estimativa pontual."""
    n = x.shape[0]
    if reamostras == 0:
        return np.empty((0, *beta.shape)), np.empty(0)
    gerador = np.random.default_rng(semente)
    vezes = np.zeros((reamostras, n))
    for indice in range(reamostras):
        vezes[indice] = np.bincount(gerador.integers(0, n, n), minlength=n)
    gram, cruzado = _normais(x, y, vezes * contas.sum(axis=1)[None, :])
    inicio = np.broadcast_to(beta, (reamostras, *beta.shape)).copy()
    amostras = _fista(gram, cruzado, inicio)
    votos = vezes @ contas
    partes = np.array(
        [_parte(amostras[indice], votos[indice], eliminados) for indice in range(reamostras)]
    )
    return amostras, partes


def _parte(beta: _Matriz, votos: _Vetor, eliminados: tuple[int, ...]) -> float:
    if not eliminados:
        return 0.5
    linhas = list(eliminados)
    para_a = float(votos[linhas] @ beta[linhas, 0])
    para_finalistas = para_a + float(votos[linhas] @ beta[linhas, 1])
    if para_finalistas <= 0:
        return 0.5
    return para_a / para_finalistas


def _posicoes(indices: tuple[int, ...], presentes: npt.NDArray[np.intp]) -> tuple[int, ...]:
    onde = {int(original): posicao for posicao, original in enumerate(presentes)}
    return tuple(onde[indice] for indice in indices if indice in onde)


def _linhas(
    beta: _Matriz,
    amostras: _Matriz,
    contas: _Matriz,
    presentes: npt.NDArray[np.intp],
    chaves: tuple[str, ...],
    nivel: float,
) -> tuple[LinhaDeTransferencia, ...]:
    votos = contas.sum(axis=0)
    found: list[LinhaDeTransferencia] = []
    for posicao, original in enumerate(presentes):
        a, b, branco = (
            _taxa(float(beta[posicao, destino]), amostras[:, posicao, destino], nivel)
            for destino in range(len(DESTINOS))
        )
        found.append(
            LinhaDeTransferencia(chaves[int(original)], int(votos[posicao]), (a, b, branco))
        )
    return tuple(found)


def _taxa(estimada: float, amostras: _Vetor, nivel: float) -> Taxa:
    if amostras.size == 0:
        return Taxa(estimada, estimada, estimada)
    cauda = (1.0 - nivel) / 2.0
    inferior, superior = np.quantile(amostras, (cauda, 1.0 - cauda))
    return Taxa(estimada, float(inferior), float(superior))


def _r2(x: _Matriz, y: _Matriz, pesos: _Vetor, beta: _Matriz) -> float:
    """R² ponderado da fatia de A no 2º turno."""
    real = y[:, 0]
    previsto = x @ beta[:, 0]
    media = float(np.average(real, weights=pesos))
    total = float(np.sum(pesos * (real - media) ** 2))
    if total <= 0:
        return 0.0
    return 1.0 - float(np.sum(pesos * (real - previsto) ** 2)) / total


def _rmse(x: _Matriz, y: _Matriz, pesos: _Vetor, beta: _Matriz) -> float:
    """Raiz do erro quadrático médio ponderado, nas três fatias do 2º turno."""
    erros = ((y - x @ beta) ** 2).sum(axis=1) / y.shape[1]
    return float(np.sqrt(np.average(erros, weights=pesos)))
