"""1º × 2º turno de presidente seção por seção: resíduo, z robusto e verificações.

As seções se pareiam por (UF, município, zona, seção). Cada cenário de
``mapa_turnos`` dá a fatia esperada do finalista A entre os dois finalistas;
o resíduo é a fatia real menos a esperada. O z robusto compara o resíduo
com a mediana e o MAD das seções do mesmo município. Município com menos de
``MINIMO_NO_GRUPO`` seções comparáveis cai para a zona, e a zona pequena cai
para a UF. Seção com menos de ``PISO_DA_SECAO`` votos de finalista não entra
na conta do z.

As verificações objetivas (cédulas acima dos aptos, cédulas que mudam muito
entre os turnos, aptos que mudam entre os turnos) não dependem de cenário e
ficam separadas do z. Nenhuma das duas coisas prova fraude: o z só aponta onde
o cenário explica mal o voto da seção, e com dezenas de milhares de seções
alguns |z| altos aparecem por acaso.
"""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from math import erfc, sqrt
from statistics import median
from typing import Final, TypeAlias

from eleicoes.domain.boletim_consulta import VotosSecao
from eleicoes.domain.mapa_turnos import (
    LIMIAR_FORA,
    LIMIAR_MODERADO,
    MINIMO_NO_GRUPO,
    SEM_BASE,
    Apuracao,
    Cenario,
    Leitura,
    _comparavel,
    _escala,
    _esperado_e_real,
    _votos_de_diferenca,
    cenarios,
    classe_do_z,
    finalistas,
)
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.domain.values import UF_CODES, uf_name

PISO_DA_SECAO: Final = 150
"""Votos válidos no 1º turno e votos de finalista no 2º. O MAD não olha o tamanho
da seção, e na seção pequena o acaso pesa: com 100 votos o desvio padrão
binomial da fatia é de uns 5 pontos, com 150 de uns 4. No 2º turno de AC, AL,
AM e AP, com piso de 100, a faixa de 100 a 149 votos tinha de 1% a 2,3% das
seções com |z| > 3,5, contra 0,3% a 0,4% na de 150 a 249 e menos de 0,2% acima
de 250. Por isso o piso fica em 150."""

VARIACAO_DE_CEDULAS: Final = Fraction(1, 2)
DIFERENCA_MINIMA_DE_CEDULAS: Final = 20
VARIACAO_DE_APTOS: Final = Fraction(1, 20)
DIFERENCA_MINIMA_DE_APTOS: Final = 10
DESTAQUES_POR_UF: Final = 100

GRUPO_MUNICIPIO: Final = "municipio"
GRUPO_ZONA: Final = "zona"
GRUPO_UF: Final = "uf"
GRUPO_NENHUM: Final = ""
GRUPOS: Final = (GRUPO_MUNICIPIO, GRUPO_ZONA, GRUPO_UF, GRUPO_NENHUM)

ACIMA_DOS_APTOS: Final = "acima_dos_aptos"
CEDULAS_DESTOANTES: Final = "cedulas_destoantes"
APTOS_MUDARAM: Final = "aptos_mudaram"
ALERTAS: Final = (ACIMA_DOS_APTOS, CEDULAS_DESTOANTES, APTOS_MUDARAM)

_CORTES_DAS_FAIXAS: Final = (250, 400)
_PARTIDO_MAXIMO: Final = 99
_Grupo: TypeAlias = tuple[str, int, int]


@dataclass(frozen=True, slots=True)
class SecaoTurnos:
    uf: str
    municipio: int
    nome: str
    zona: int
    secao: int
    aptos: tuple[int, int]
    complemento: tuple[int, int]
    primeiro: Apuracao
    segundo: Apuracao
    comparavel: bool
    grupo: str
    leituras: tuple[Leitura, ...]
    alertas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContagemCenario:
    """Contagem de z de um cenário, com o que a normal esperaria por acaso."""

    com_z: int
    fora_a: int
    fora_b: int
    moderados: int

    @property
    def fora(self) -> int:
        return self.fora_a + self.fora_b

    @property
    def fora_esperado(self) -> float:
        return self.com_z * cauda_normal(LIMIAR_FORA)

    @property
    def acima_de_dois(self) -> int:
        return self.fora + self.moderados

    @property
    def acima_de_dois_esperado(self) -> float:
        return self.com_z * cauda_normal(LIMIAR_MODERADO)

    def __add__(self, other: "ContagemCenario") -> "ContagemCenario":
        return ContagemCenario(
            self.com_z + other.com_z,
            self.fora_a + other.fora_a,
            self.fora_b + other.fora_b,
            self.moderados + other.moderados,
        )


@dataclass(frozen=True, slots=True)
class ResumoUf:
    uf: str
    nome: str
    pareadas: int
    so_no_primeiro: int
    so_no_segundo: int
    abaixo_do_piso: int
    por_grupo: tuple[int, ...]
    cenarios: tuple[ContagemCenario, ...]
    alertas: tuple[int, ...]

    @property
    def comparaveis(self) -> int:
        return self.pareadas - self.abaixo_do_piso

    def __add__(self, other: "ResumoUf") -> "ResumoUf":
        return ResumoUf(
            self.uf,
            self.nome,
            self.pareadas + other.pareadas,
            self.so_no_primeiro + other.so_no_primeiro,
            self.so_no_segundo + other.so_no_segundo,
            self.abaixo_do_piso + other.abaixo_do_piso,
            _somados(self.por_grupo, other.por_grupo),
            tuple(
                mine + theirs for mine, theirs in zip(self.cenarios, other.cenarios, strict=True)
            ),
            _somados(self.alertas, other.alertas),
        )


@dataclass(frozen=True, slots=True)
class FaixaDeVotos:
    """Seções com z numa faixa de votos de finalista no 2º turno, e quantas passam de 3,5."""

    minimo: int
    maximo: int | None
    secoes: int
    fora: int


@dataclass(frozen=True, slots=True)
class AnaliseSecoes:
    a: int
    b: int
    cenarios: tuple[Cenario, ...]
    piso: int
    minimo: int
    secoes: tuple[SecaoTurnos, ...]
    resumos: tuple[ResumoUf, ...]
    total: ResumoUf
    faixas: tuple[tuple[FaixaDeVotos, ...], ...]


def analisar_secoes(
    primeiro: Mapping[str, Sequence[VotosSecao]],
    segundo: Mapping[str, Sequence[VotosSecao]],
    nomes: Mapping[str, Mapping[int, str]],
    *,
    apoiado: int | None = None,
    piso: int = PISO_DA_SECAO,
    minimo: int = MINIMO_NO_GRUPO,
) -> AnaliseSecoes:
    """Pareia as seções das UFs que já têm 2º turno e lê cada uma sob cada cenário."""
    a, b = _finalistas(segundo, apoiado)
    escolhidos = cenarios(a, b)
    secoes: list[SecaoTurnos] = []
    resumos: list[ResumoUf] = []
    for uf in _ufs(segundo):
        lidas, resumo = _uf(
            uf,
            primeiro.get(uf, ()),
            segundo[uf],
            nomes.get(uf, {}),
            (a, b, escolhidos),
            (piso, minimo),
        )
        secoes.extend(lidas)
        resumos.append(resumo)
    total = _total(resumos, len(escolhidos))
    faixas = tuple(_faixas(secoes, indice, piso) for indice in range(len(escolhidos)))
    return AnaliseSecoes(
        a, b, escolhidos, piso, minimo, tuple(secoes), tuple(resumos), total, faixas
    )


def destaques(
    analise: AnaliseSecoes,
    indice: int,
    por_uf: int = DESTAQUES_POR_UF,
) -> tuple[SecaoTurnos, ...]:
    """As seções de maior |z| num cenário, até ``por_uf`` em cada UF, da maior para a menor."""
    escolhidas: list[SecaoTurnos] = []
    for resumo in analise.resumos:
        da_uf = [
            secao
            for secao in analise.secoes
            if secao.uf == resumo.uf and secao.leituras[indice].z is not None
        ]
        da_uf.sort(key=lambda secao: _modulo(secao, indice), reverse=True)
        escolhidas.extend(da_uf[:por_uf])
    escolhidas.sort(key=lambda secao: _modulo(secao, indice), reverse=True)
    return tuple(escolhidas)


def com_alerta(analise: AnaliseSecoes) -> tuple[SecaoTurnos, ...]:
    return tuple(secao for secao in analise.secoes if secao.alertas)


def cauda_normal(limiar: float) -> float:
    """P(|Z| > limiar) para Z normal padrão."""
    return erfc(limiar / sqrt(2))


def apuracao_da_secao(votos: VotosSecao, a: int, b: int) -> Apuracao:
    outros = sum(total for numero, total in votos.nominais if numero not in (a, b))
    return Apuracao(votos.votos(a), votos.votos(b), outros, votos.branco, votos.nulo)


def alertas_da_secao(antes: VotosSecao, depois: VotosSecao) -> tuple[str, ...]:
    found: list[str] = []
    if antes.cedulas > antes.eleitores_aptos or depois.cedulas > depois.eleitores_aptos:
        found.append(ACIMA_DOS_APTOS)
    if _destoa(antes.cedulas, depois.cedulas, VARIACAO_DE_CEDULAS, DIFERENCA_MINIMA_DE_CEDULAS):
        found.append(CEDULAS_DESTOANTES)
    if _destoa(
        antes.eleitores_aptos,
        depois.eleitores_aptos,
        VARIACAO_DE_APTOS,
        DIFERENCA_MINIMA_DE_APTOS,
    ):
        found.append(APTOS_MUDARAM)
    return tuple(found)


def _destoa(antes: int, depois: int, variacao: Fraction, minima: int) -> bool:
    diferenca = abs(depois - antes)
    return diferenca >= minima and diferenca > variacao * antes


def _finalistas(
    segundo: Mapping[str, Sequence[VotosSecao]], apoiado: int | None
) -> tuple[int, int]:
    lugares: list[MunicipalPlace] = []
    for uf, secoes in segundo.items():
        totais: Counter[int] = Counter()
        for votos in secoes:
            for numero, total in votos.nominais:
                totais[numero] += total
        partes = tuple(
            PartyTally(numero, total, 0)
            for numero, total in sorted(totais.items())
            if total > 0 and numero <= _PARTIDO_MAXIMO
        )
        if partes:
            lugares.append(MunicipalPlace(uf, uf, uf, CargoTally(partes, 0, 0), None))
    return finalistas(lugares, apoiado)


def _ufs(segundo: Mapping[str, Sequence[VotosSecao]]) -> tuple[str, ...]:
    return tuple(uf for uf in UF_CODES if segundo.get(uf))


def _uf(
    uf: str,
    antes: Sequence[VotosSecao],
    depois: Sequence[VotosSecao],
    nomes: Mapping[int, str],
    finais: tuple[int, int, tuple[Cenario, ...]],
    limites: tuple[int, int],
) -> tuple[tuple[SecaoTurnos, ...], ResumoUf]:
    a, b, escolhidos = finais
    piso, minimo = limites
    anteriores = {_chave(votos): votos for votos in antes}
    posteriores = {_chave(votos): votos for votos in depois}
    pares = tuple(
        (anteriores[chave], posteriores[chave])
        for chave in sorted(posteriores)
        if chave in anteriores
    )
    contas = tuple(
        (apuracao_da_secao(velho, a, b), apuracao_da_secao(novo, a, b)) for velho, novo in pares
    )
    comparaveis = tuple(_comparavel(um, dois, piso) for um, dois in contas)
    grupos = _grupos(pares, comparaveis, minimo)
    lugares = tuple((velho.municipio, velho.zona) for velho, _novo in pares)
    por_cenario = tuple(
        _leituras(contas, comparaveis, grupos, lugares, cenario, minimo) for cenario in escolhidos
    )
    secoes = tuple(
        SecaoTurnos(
            uf,
            velho.municipio,
            nomes.get(velho.municipio, str(velho.municipio)),
            velho.zona,
            velho.secao,
            (velho.eleitores_aptos, novo.eleitores_aptos),
            (velho.eleitores_complemento, novo.eleitores_complemento),
            um,
            dois,
            comparaveis[indice],
            grupos[indice][0],
            tuple(lidas[indice] for lidas in por_cenario),
            alertas_da_secao(velho, novo),
        )
        for indice, ((velho, novo), (um, dois)) in enumerate(zip(pares, contas, strict=True))
    )
    sozinhos = (
        sum(1 for chave in anteriores if chave not in posteriores),
        sum(1 for chave in posteriores if chave not in anteriores),
    )
    return secoes, _resumo(uf, uf_name(uf), secoes, sozinhos, len(escolhidos))


def _chave(votos: VotosSecao) -> tuple[int, int, int]:
    return (votos.municipio, votos.zona, votos.secao)


def _grupos(
    pares: Sequence[tuple[VotosSecao, VotosSecao]],
    comparaveis: Sequence[bool],
    minimo: int,
) -> tuple[_Grupo, ...]:
    """O grupo de referência de cada seção: município, zona ou UF, o menor que tiver base."""
    por_municipio: Counter[int] = Counter()
    por_zona: Counter[int] = Counter()
    for (velho, _novo), comparavel in zip(pares, comparaveis, strict=True):
        if comparavel:
            por_municipio[velho.municipio] += 1
            por_zona[velho.zona] += 1
    na_uf = sum(comparaveis)
    found: list[_Grupo] = []
    for velho, _novo in pares:
        if por_municipio[velho.municipio] >= minimo:
            found.append((GRUPO_MUNICIPIO, velho.municipio, 0))
        elif por_zona[velho.zona] >= minimo:
            found.append((GRUPO_ZONA, 0, velho.zona))
        elif na_uf >= minimo:
            found.append((GRUPO_UF, 0, 0))
        else:
            found.append((GRUPO_NENHUM, 0, 0))
    return tuple(found)


def _leituras(
    contas: Sequence[tuple[Apuracao, Apuracao]],
    comparaveis: Sequence[bool],
    grupos: Sequence[_Grupo],
    lugares: Sequence[tuple[int, int]],
    cenario: Cenario,
    minimo: int,
) -> tuple[Leitura, ...]:
    brutos = tuple(_esperado_e_real(um, dois, cenario) for um, dois in contas)
    residuos = tuple(float(real - esperado) for esperado, real in brutos)
    medidas = _medidas(residuos, comparaveis, grupos, lugares, minimo)
    found: list[Leitura] = []
    for indice, (esperado, real) in enumerate(brutos):
        diferenca = _votos_de_diferenca(contas[indice][1], esperado, real)
        medida = medidas.get(grupos[indice]) if comparaveis[indice] else None
        if medida is None:
            found.append(Leitura(esperado, real, diferenca, None, SEM_BASE))
            continue
        centro, escala = medida
        z = (residuos[indice] - centro) / escala
        found.append(Leitura(esperado, real, diferenca, z, classe_do_z(z)))
    return tuple(found)


def _medidas(
    residuos: Sequence[float],
    comparaveis: Sequence[bool],
    grupos: Sequence[_Grupo],
    lugares: Sequence[tuple[int, int]],
    minimo: int,
) -> dict[_Grupo, tuple[float, float]]:
    """Mediana e escala de cada grupo usado, sobre todas as seções comparáveis dele.

    A zona de um município pequeno inclui as seções dos outros municípios dela.
    """
    usados = set(grupos)
    valores: dict[_Grupo, list[float]] = {}
    for residuo, comparavel, lugar in zip(residuos, comparaveis, lugares, strict=True):
        if not comparavel:
            continue
        for referencia in _niveis(lugar):
            if referencia in usados:
                valores.setdefault(referencia, []).append(residuo)
    medidas: dict[_Grupo, tuple[float, float]] = {}
    for referencia, lista in valores.items():
        if len(lista) < minimo:
            continue
        escala = _escala(tuple(lista))
        if escala is not None:
            medidas[referencia] = (median(lista), escala)
    return medidas


def _niveis(lugar: tuple[int, int]) -> tuple[_Grupo, ...]:
    municipio, zona = lugar
    return (
        (GRUPO_MUNICIPIO, municipio, 0),
        (GRUPO_ZONA, 0, zona),
        (GRUPO_UF, 0, 0),
    )


def _resumo(
    uf: str,
    nome: str,
    secoes: Sequence[SecaoTurnos],
    sozinhos: tuple[int, int],
    quantos: int,
) -> ResumoUf:
    return ResumoUf(
        uf,
        nome,
        len(secoes),
        sozinhos[0],
        sozinhos[1],
        sum(1 for secao in secoes if not secao.comparavel),
        tuple(sum(1 for secao in secoes if secao.grupo == grupo) for grupo in GRUPOS),
        tuple(_contagem(secoes, indice) for indice in range(quantos)),
        tuple(sum(1 for secao in secoes if alerta in secao.alertas) for alerta in ALERTAS),
    )


def _contagem(secoes: Sequence[SecaoTurnos], indice: int) -> ContagemCenario:
    classes = Counter(secao.leituras[indice].classe for secao in secoes)
    com_z = sum(1 for secao in secoes if secao.leituras[indice].z is not None)
    return ContagemCenario(com_z, classes["fora_a"], classes["fora_b"], classes["moderado"])


def _total(resumos: Sequence[ResumoUf], quantos: int) -> ResumoUf:
    vazio = ResumoUf(
        "",
        "Todas as UFs",
        0,
        0,
        0,
        0,
        tuple(0 for _ in GRUPOS),
        tuple(ContagemCenario(0, 0, 0, 0) for _ in range(quantos)),
        tuple(0 for _ in ALERTAS),
    )
    total = vazio
    for resumo in resumos:
        total = total + resumo
    return total


def _limites_das_faixas(piso: int) -> tuple[tuple[int, int | None], ...]:
    inicios = (piso, *(corte for corte in _CORTES_DAS_FAIXAS if corte > piso))
    fins: tuple[int | None, ...] = (*(inicio - 1 for inicio in inicios[1:]), None)
    return tuple(zip(inicios, fins, strict=True))


def _faixas(secoes: Sequence[SecaoTurnos], indice: int, piso: int) -> tuple[FaixaDeVotos, ...]:
    found: list[FaixaDeVotos] = []
    for minimo, maximo in _limites_das_faixas(piso):
        dentro = _na_faixa(minimo, maximo)
        lidas = tuple(
            secao.leituras[indice]
            for secao in secoes
            if dentro(secao.segundo.a + secao.segundo.b) and secao.leituras[indice].z is not None
        )
        fora = sum(1 for leitura in lidas if abs(leitura.z or 0.0) > LIMIAR_FORA)
        found.append(FaixaDeVotos(minimo, maximo, len(lidas), fora))
    return tuple(found)


def _na_faixa(minimo: int, maximo: int | None) -> Callable[[int], bool]:
    def dentro(votos: int) -> bool:
        return votos >= minimo and (maximo is None or votos <= maximo)

    return dentro


def _modulo(secao: SecaoTurnos, indice: int) -> float:
    return abs(secao.leituras[indice].z or 0.0)


def _somados(mine: tuple[int, ...], theirs: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(um + outro for um, outro in zip(mine, theirs, strict=True))
