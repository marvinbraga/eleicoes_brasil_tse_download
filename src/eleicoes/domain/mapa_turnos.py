"""1º × 2º turno de presidente: variação, cenários de transferência e desvio local.

O modelo de cada cenário só redistribui os votos dos candidatos eliminados.
A fatia esperada do finalista A entre os votos dos dois finalistas é

    (A₁ + f·O₁) / (A₁ + B₁ + O₁)

em que O₁ soma os eliminados e f é a parte que vai para A. O cenário
proporcional (f = A₁ / (A₁ + B₁)) equivale a manter a fatia de A₁ entre os
dois. O resíduo é a fatia real menos a esperada. O desvio local compara o
resíduo de cada lugar com a mediana dos lugares do mesmo grupo (a UF, para
municípios) pelo z robusto de Iglewicz e Hoaglin. Desvio grande não prova
nada sobre a apuração: só aponta onde o cenário explica mal o voto.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from statistics import median
from typing import Final

from eleicoes.domain.errors import ElectionError
from eleicoes.domain.mapa import PonteTseIbge
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace
from eleicoes.domain.values import UF_CODES, uf_name

PISO_DE_VOTOS: Final = 1000
MINIMO_NO_GRUPO: Final = 8
LIMIAR_MODERADO: Final = 2.0
LIMIAR_FORA: Final = 3.5
_K_MAD: Final = 0.6745
_K_MEDIA: Final = 0.7979
_EXTERIOR: Final = "ZZ"
_PAIS_NOME: Final = "Brasil"

DENTRO: Final = "dentro"
MODERADO: Final = "moderado"
FORA_A: Final = "fora_a"
FORA_B: Final = "fora_b"
SEM_BASE: Final = "sem_base"


class FinalistsMissingError(ElectionError):
    def __init__(self) -> None:
        super().__init__("second round has fewer than two candidates")


@dataclass(frozen=True, slots=True)
class Apuracao:
    """Votos de presidente de um turno num lugar, já separados pelos finalistas."""

    a: int
    b: int
    outros: int
    branco: int
    nulo: int

    @property
    def validos(self) -> int:
        return self.a + self.b + self.outros

    @property
    def cedulas(self) -> int:
        return self.validos + self.branco + self.nulo

    def __add__(self, other: "Apuracao") -> "Apuracao":
        return Apuracao(
            self.a + other.a,
            self.b + other.b,
            self.outros + other.outros,
            self.branco + other.branco,
            self.nulo + other.nulo,
        )


@dataclass(frozen=True, slots=True)
class Cenario:
    chave: str
    rotulo: str
    descricao: str
    parte_de_a: Fraction | None

    def parte(self, primeiro: Apuracao) -> Fraction:
        if self.parte_de_a is not None:
            return self.parte_de_a
        finalistas = primeiro.a + primeiro.b
        if finalistas == 0:
            return Fraction(1, 2)
        return Fraction(primeiro.a, finalistas)


@dataclass(frozen=True, slots=True)
class Leitura:
    """Um lugar sob um cenário. Fatias de A entre os votos dos dois finalistas."""

    esperado: Fraction
    real: Fraction
    votos_de_diferenca: int
    z: float | None
    classe: str

    @property
    def residuo(self) -> Fraction:
        return self.real - self.esperado


@dataclass(frozen=True, slots=True)
class LugarTurnos:
    codigo: str
    nome: str
    uf: str
    primeiro: Apuracao
    segundo: Apuracao
    leituras: tuple[Leitura, ...]


@dataclass(frozen=True, slots=True)
class PontoTurnos:
    lugar: LugarTurnos
    lon: float
    lat: float


@dataclass(frozen=True, slots=True)
class ComparativoTurnos:
    a: int
    b: int
    cenarios: tuple[Cenario, ...]
    pais: LugarTurnos | None
    ufs: tuple[LugarTurnos, ...]
    municipios: tuple[LugarTurnos, ...]
    exterior: tuple[PontoTurnos, ...]
    ufs_com_segundo: tuple[str, ...]
    sem_comparacao: int
    sem_poligono: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Par:
    uf: str
    codigo: str
    nome: str
    primeiro: Apuracao
    segundo: Apuracao


def cenarios(a: int, b: int) -> tuple[Cenario, ...]:
    return (
        Cenario(
            "todosa",
            f"Todos apoiam o {a}",
            f"Os votos dos eliminados vão todos para o {a}.",
            Fraction(1),
        ),
        Cenario(
            "maioriaa",
            f"75% para o {a}",
            f"Três quartos dos votos dos eliminados vão para o {a} e um quarto para o {b}.",
            Fraction(3, 4),
        ),
        Cenario(
            "dividido",
            "Metade para cada",
            "Os votos dos eliminados se dividem igualmente entre os dois finalistas.",
            Fraction(1, 2),
        ),
        Cenario(
            "proporcional",
            "Como no 1º turno",
            "Os eliminados se dividem como os eleitores dos finalistas no 1º turno, "
            "o mesmo que não pesarem no resultado.",
            None,
        ),
        Cenario(
            "maioriab",
            f"75% para o {b}",
            f"Três quartos dos votos dos eliminados vão para o {b} e um quarto para o {a}.",
            Fraction(1, 4),
        ),
    )


def finalistas(segundo: Sequence[MunicipalPlace], apoiado: int | None = None) -> tuple[int, int]:
    """Os dois mais votados do 2º turno. O apoiado pelos eliminados, se for um deles, vem antes."""
    totais: dict[int, int] = {}
    for place in segundo:
        for party in place.presidente.parties:
            totais[party.partido] = totais.get(party.partido, 0) + party.votos
    ordem = sorted(totais, key=lambda numero: (-totais[numero], numero))
    if len(ordem) < 2:
        raise FinalistsMissingError
    lider, vice = ordem[0], ordem[1]
    if apoiado == vice:
        return vice, lider
    return lider, vice


def comparar_turnos(
    primeiro: Sequence[MunicipalPlace],
    segundo: Sequence[MunicipalPlace],
    ponte: PonteTseIbge,
    codigos_municipio: frozenset[str],
    codigos_uf: frozenset[str],
    brasil_id: str,
    *,
    exterior: Mapping[str, tuple[float, float]] | None = None,
    apoiado: int | None = None,
) -> ComparativoTurnos:
    a, b = finalistas(segundo, apoiado)
    escolhidos = cenarios(a, b)
    pares, sem_comparacao = _pares(primeiro, segundo, a, b)
    cidades = tuple(par for par in pares if par.uf != _EXTERIOR)
    fora = tuple(par for par in pares if par.uf == _EXTERIOR)
    municipios, buracos = _municipios(cidades, escolhidos, ponte, codigos_municipio)
    pontos, buracos_exterior = _exterior(fora, escolhidos, exterior or {})
    ufs, buracos_uf = _ufs(pares, escolhidos, ponte, codigos_uf)
    pais = _pais(pares, escolhidos, brasil_id)
    return ComparativoTurnos(
        a,
        b,
        escolhidos,
        pais,
        ufs,
        municipios,
        pontos,
        tuple(code for code in UF_CODES if any(par.uf == code for par in pares)),
        sem_comparacao,
        tuple(sorted(buracos + buracos_exterior + buracos_uf)),
    )


def leituras(
    pares: Sequence[tuple[Apuracao, Apuracao]],
    cenario: Cenario,
    *,
    piso: int = PISO_DE_VOTOS,
    minimo: int = MINIMO_NO_GRUPO,
) -> tuple[Leitura, ...]:
    """Lê um grupo de lugares sob um cenário e mede o desvio de cada um no grupo."""
    brutos = tuple(_esperado_e_real(primeiro, segundo, cenario) for primeiro, segundo in pares)
    base = tuple(
        float(real - esperado)
        for (primeiro, segundo), (esperado, real) in zip(pares, brutos, strict=True)
        if _comparavel(primeiro, segundo, piso)
    )
    escala = _escala(base) if len(base) >= minimo else None
    centro = median(base) if escala is not None else 0.0
    found: list[Leitura] = []
    for (primeiro, segundo), (esperado, real) in zip(pares, brutos, strict=True):
        diferenca = _votos_de_diferenca(segundo, esperado, real)
        if escala is None or not _comparavel(primeiro, segundo, piso):
            found.append(Leitura(esperado, real, diferenca, None, SEM_BASE))
            continue
        z = (float(real - esperado) - centro) / escala
        found.append(Leitura(esperado, real, diferenca, z, classe_do_z(z)))
    return tuple(found)


def classe_do_z(z: float) -> str:
    if z > LIMIAR_FORA:
        return FORA_A
    if z < -LIMIAR_FORA:
        return FORA_B
    if abs(z) > LIMIAR_MODERADO:
        return MODERADO
    return DENTRO


def apuracao(tally: CargoTally, a: int, b: int) -> Apuracao:
    votos = {party.partido: party.votos for party in tally.parties}
    outros = sum(total for numero, total in votos.items() if numero not in (a, b))
    return Apuracao(
        votos.get(a, 0),
        votos.get(b, 0),
        outros,
        tally.branco,
        tally.nulo,
    )


def chave_tse(codigo: str) -> str:
    if codigo.isdigit() and len(codigo) < 5:
        return codigo.zfill(5)
    return codigo


def _esperado_e_real(
    primeiro: Apuracao, segundo: Apuracao, cenario: Cenario
) -> tuple[Fraction, Fraction]:
    finalistas_1 = primeiro.validos
    esperado = (
        Fraction(1, 2)
        if finalistas_1 == 0
        else (primeiro.a + cenario.parte(primeiro) * primeiro.outros) / finalistas_1
    )
    finalistas_2 = segundo.a + segundo.b
    real = Fraction(1, 2) if finalistas_2 == 0 else Fraction(segundo.a, finalistas_2)
    return esperado, real


def _votos_de_diferenca(segundo: Apuracao, esperado: Fraction, real: Fraction) -> int:
    return round((real - esperado) * (segundo.a + segundo.b))


def _comparavel(primeiro: Apuracao, segundo: Apuracao, piso: int) -> bool:
    return primeiro.validos >= piso and segundo.a + segundo.b >= piso


def _escala(valores: tuple[float, ...]) -> float | None:
    centro = median(valores)
    desvios = tuple(abs(valor - centro) for valor in valores)
    mad = median(desvios)
    if mad > 0:
        return mad / _K_MAD
    media = sum(desvios) / len(desvios)
    if media > 0:
        return media / _K_MEDIA
    return None


def _pares(
    primeiro: Sequence[MunicipalPlace],
    segundo: Sequence[MunicipalPlace],
    a: int,
    b: int,
) -> tuple[tuple[_Par, ...], int]:
    antes = {(place.uf, chave_tse(place.codigo)): place for place in primeiro}
    depois = {(place.uf, chave_tse(place.codigo)): place for place in segundo}
    ufs_depois = {uf for uf, _ in depois}
    found: list[_Par] = []
    for chave, place in depois.items():
        anterior = antes.get(chave)
        if anterior is None:
            continue
        uf, codigo = chave
        found.append(
            _Par(
                uf,
                codigo,
                place.nome,
                apuracao(anterior.presidente, a, b),
                apuracao(place.presidente, a, b),
            )
        )
    sozinhos = sum(1 for chave in antes if chave[0] in ufs_depois and chave not in depois)
    sozinhos += sum(1 for chave in depois if chave not in antes)
    ordem = {code: indice for indice, code in enumerate(UF_CODES)}
    found.sort(key=lambda par: (ordem.get(par.uf, len(ordem)), par.codigo))
    return tuple(found), sozinhos


def _lugares(
    grupo: Sequence[_Par],
    escolhidos: tuple[Cenario, ...],
    codigo: Callable[[_Par], str],
) -> tuple[LugarTurnos, ...]:
    contas = tuple((par.primeiro, par.segundo) for par in grupo)
    por_cenario = tuple(leituras(contas, cenario) for cenario in escolhidos)
    return tuple(
        LugarTurnos(
            codigo(par),
            par.nome,
            par.uf,
            par.primeiro,
            par.segundo,
            tuple(lidas[indice] for lidas in por_cenario),
        )
        for indice, par in enumerate(grupo)
    )


def _municipios(
    cidades: tuple[_Par, ...],
    escolhidos: tuple[Cenario, ...],
    ponte: PonteTseIbge,
    codigos: frozenset[str],
) -> tuple[tuple[LugarTurnos, ...], tuple[str, ...]]:
    lugares: list[LugarTurnos] = []
    buracos: list[str] = []
    for uf in UF_CODES:
        grupo = tuple(par for par in cidades if par.uf == uf)
        if not grupo:
            continue
        lidos = _lugares(grupo, escolhidos, lambda par: ponte.municipio_por_tse.get(par.codigo, ""))
        for lugar in lidos:
            if lugar.codigo in codigos:
                lugares.append(lugar)
            else:
                buracos.append(lugar.nome)
    return tuple(lugares), tuple(buracos)


def _exterior(
    fora: tuple[_Par, ...],
    escolhidos: tuple[Cenario, ...],
    coordenadas: Mapping[str, tuple[float, float]],
) -> tuple[tuple[PontoTurnos, ...], tuple[str, ...]]:
    pontos: list[PontoTurnos] = []
    buracos: list[str] = []
    for lugar in _lugares(fora, escolhidos, lambda par: par.codigo):
        coordenada = coordenadas.get(lugar.codigo)
        if coordenada is None:
            buracos.append(lugar.nome)
            continue
        pontos.append(PontoTurnos(lugar, coordenada[0], coordenada[1]))
    return tuple(pontos), tuple(buracos)


def _ufs(
    pares: tuple[_Par, ...],
    escolhidos: tuple[Cenario, ...],
    ponte: PonteTseIbge,
    codigos: frozenset[str],
) -> tuple[tuple[LugarTurnos, ...], tuple[str, ...]]:
    somados: list[_Par] = []
    buracos: list[str] = []
    for uf in UF_CODES:
        grupo = tuple(par for par in pares if par.uf == uf)
        if not grupo:
            continue
        ibge = ponte.uf_por_sigla.get(uf)
        if uf == _EXTERIOR or ibge is None or ibge not in codigos:
            buracos.append(f"{uf_name(uf)} ({uf})")
            continue
        somados.append(_soma(grupo, uf, ibge, uf_name(uf)))
    lidos = _lugares(somados, escolhidos, lambda par: par.codigo)
    return lidos, tuple(buracos)


def _pais(
    pares: tuple[_Par, ...],
    escolhidos: tuple[Cenario, ...],
    brasil_id: str,
) -> LugarTurnos | None:
    if not pares:
        return None
    somado = _soma(pares, "BR", brasil_id, _PAIS_NOME)
    return _lugares((somado,), escolhidos, lambda par: par.codigo)[0]


def _soma(grupo: Sequence[_Par], uf: str, codigo: str, nome: str) -> _Par:
    primeiro = grupo[0].primeiro
    segundo = grupo[0].segundo
    for par in grupo[1:]:
        primeiro = primeiro + par.primeiro
        segundo = segundo + par.segundo
    return _Par(uf, codigo, nome, primeiro, segundo)
