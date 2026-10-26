"""Calibra os limiares do desvio local do 1º × 2º turno numa eleição sem contestação.

Roda nos municípios de uma eleição passada a mesma conta do mapa
(`mapa_turnos.leituras`, agrupada por UF, com o mesmo piso e o mesmo grupo
mínimo) e mede quantos lugares cada limiar marcaria. Numa eleição aceita como
limpa, a fatia marcada é o ruído normal do modelo: o limiar só serve se essa
fatia for pequena.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.mapa_turnos import (
    FORA_A,
    FORA_B,
    LIMIAR_FORA,
    LIMIAR_MODERADO,
    MINIMO_NO_GRUPO,
    MODERADO,
    PISO_DE_VOTOS,
    Apuracao,
    Cenario,
    Leitura,
    apuracao,
    cenarios,
    chave_tse,
    leituras,
)
from eleicoes.domain.presidente_governador import MunicipalPlace
from eleicoes.domain.values import UF_CODES

QUANTIS: Final = (0.9, 0.95, 0.99, 0.995, 0.999)
FRACOES_ALVO: Final = (0.01, 0.001)
METODO_DO_QUANTIL: Final = "interpolação linear entre as ordens (tipo 7 de Hyndman e Fan)"
_EXTERIOR: Final = "ZZ"
_CASAS: Final = 6


@dataclass(frozen=True, slots=True)
class ParMunicipal:
    uf: str
    codigo: str
    nome: str
    primeiro: Apuracao
    segundo: Apuracao


@dataclass(frozen=True, slots=True)
class Contagem:
    """Quantos lugares de um grupo caíram em cada classe do desvio local."""

    lugares: int
    com_base: int
    moderados: int
    fora_a: int
    fora_b: int

    @property
    def sem_base(self) -> int:
        return self.lugares - self.com_base

    @property
    def fora(self) -> int:
        return self.fora_a + self.fora_b

    @property
    def acima_do_moderado(self) -> int:
        return self.moderados + self.fora


@dataclass(frozen=True, slots=True)
class Limiar:
    fracao_alvo: float
    abs_z: float
    marcados: int


@dataclass(frozen=True, slots=True)
class AjusteNacional:
    """O país inteiro, exterior incluído, como no `_pais` do mapa."""

    esperado: Fraction
    real: Fraction
    votos_de_diferenca: int

    @property
    def residuo(self) -> Fraction:
        return self.real - self.esperado


@dataclass(frozen=True, slots=True)
class CalibracaoCenario:
    cenario: Cenario
    nacional: AjusteNacional
    municipios: Contagem
    quantis: tuple[tuple[float, float], ...]
    limiares: tuple[Limiar, ...]
    fora_por_uf: tuple[tuple[str, int], ...]
    exterior: Contagem


@dataclass(frozen=True, slots=True)
class Calibracao:
    a: int
    b: int
    pareados: int
    sem_par: int
    cenarios: tuple[CalibracaoCenario, ...]

    @property
    def melhor_ajuste(self) -> CalibracaoCenario:
        """O cenário cujo esperado nacional fica mais perto do real."""
        return min(self.cenarios, key=lambda item: abs(item.nacional.residuo))


def calibrar(
    primeiro: Sequence[MunicipalPlace],
    segundo: Sequence[MunicipalPlace],
    a: int,
    b: int,
) -> Calibracao:
    pares, sem_par = parear(primeiro, segundo, a, b)
    escolhidos = tuple(_calibrar_cenario(pares, cenario) for cenario in cenarios(a, b))
    return Calibracao(a, b, len(pares), sem_par, escolhidos)


def parear(
    primeiro: Sequence[MunicipalPlace],
    segundo: Sequence[MunicipalPlace],
    a: int,
    b: int,
) -> tuple[tuple[ParMunicipal, ...], int]:
    """Junta os turnos pela UF e pelo código TSE. Devolve também os lugares sem par."""
    antes = {(place.uf, chave_tse(place.codigo)): place for place in primeiro}
    depois = {(place.uf, chave_tse(place.codigo)): place for place in segundo}
    pares = tuple(
        ParMunicipal(
            uf,
            codigo,
            depois[(uf, codigo)].nome,
            apuracao(antes[(uf, codigo)].presidente, a, b),
            apuracao(depois[(uf, codigo)].presidente, a, b),
        )
        for uf, codigo in sorted(antes.keys() & depois.keys(), key=_ordem)
    )
    return pares, len(antes.keys() ^ depois.keys())


def leituras_por_uf(
    pares: Sequence[ParMunicipal], cenario: Cenario
) -> tuple[tuple[ParMunicipal, Leitura], ...]:
    """Os municípios lidos dentro da própria UF, como em `mapa_turnos._municipios`."""
    found: list[tuple[ParMunicipal, Leitura]] = []
    for uf in UF_CODES:
        if uf == _EXTERIOR:
            continue
        grupo = tuple(par for par in pares if par.uf == uf)
        found.extend(zip(grupo, _ler(grupo, cenario), strict=True))
    return tuple(found)


def quantil(ordenados: Sequence[float], p: float) -> float:
    """Quantil por interpolação linear entre as ordens. Espera valores em ordem crescente."""
    posicao = p * (len(ordenados) - 1)
    baixo = math.floor(posicao)
    alto = min(baixo + 1, len(ordenados) - 1)
    return ordenados[baixo] + (posicao - baixo) * (ordenados[alto] - ordenados[baixo])


def limiar_para_fracao(ordenados: Sequence[float], fracao: float) -> Limiar:
    """O menor |z| observado que, com a regra estrita `|z| > limiar`, marca no máximo a fração."""
    teto = math.floor(fracao * len(ordenados))
    corte = ordenados[len(ordenados) - 1 - teto]
    marcados = sum(1 for valor in ordenados if valor > corte)
    return Limiar(fracao, corte, marcados)


def fracao_normal_acima(limiar: float) -> float:
    """P(|Z| > limiar) para Z normal padrão, a referência do z robusto."""
    return math.erfc(limiar / math.sqrt(2))


def como_json(calibracao: Calibracao, ano: int, fontes: Sequence[str]) -> dict[str, object]:
    melhor = calibracao.melhor_ajuste.cenario.chave
    return {
        "descricao": _DESCRICAO,
        "eleicao": {
            "ano": ano,
            "cargo": "presidente",
            "a": calibracao.a,
            "b": calibracao.b,
            "fontes": list(fontes),
        },
        "parametros": {
            "piso_de_votos": PISO_DE_VOTOS,
            "minimo_no_grupo": MINIMO_NO_GRUPO,
            "limiar_moderado": LIMIAR_MODERADO,
            "limiar_fora": LIMIAR_FORA,
            "agrupamento": "UF; o exterior (ZZ) é um grupo à parte",
            "metodo_do_quantil": METODO_DO_QUANTIL,
        },
        "referencia_normal": {
            "acima_do_moderado": _arredondado(fracao_normal_acima(LIMIAR_MODERADO)),
            "fora": _arredondado(fracao_normal_acima(LIMIAR_FORA)),
        },
        "municipios_pareados": calibracao.pareados,
        "sem_par": calibracao.sem_par,
        "melhor_ajuste": melhor,
        "cenarios": [_cenario_json(item) for item in calibracao.cenarios],
    }


def _calibrar_cenario(pares: Sequence[ParMunicipal], cenario: Cenario) -> CalibracaoCenario:
    lidos = leituras_por_uf(pares, cenario)
    abs_z = sorted(abs(lida.z) for _, lida in lidos if lida.z is not None)
    exterior = tuple(par for par in pares if par.uf == _EXTERIOR)
    return CalibracaoCenario(
        cenario,
        _nacional(pares, cenario),
        _contar(tuple(lida for _, lida in lidos)),
        tuple((p, quantil(abs_z, p)) for p in QUANTIS) if abs_z else (),
        tuple(limiar_para_fracao(abs_z, fracao) for fracao in FRACOES_ALVO) if abs_z else (),
        _fora_por_uf(lidos),
        _contar(_ler(exterior, cenario)),
    )


def _ler(grupo: Sequence[ParMunicipal], cenario: Cenario) -> tuple[Leitura, ...]:
    return leituras(tuple((par.primeiro, par.segundo) for par in grupo), cenario)


def _nacional(pares: Sequence[ParMunicipal], cenario: Cenario) -> AjusteNacional:
    primeiro = Apuracao(0, 0, 0, 0, 0)
    segundo = Apuracao(0, 0, 0, 0, 0)
    for par in pares:
        primeiro = primeiro + par.primeiro
        segundo = segundo + par.segundo
    (lida,) = leituras(((primeiro, segundo),), cenario)
    return AjusteNacional(lida.esperado, lida.real, lida.votos_de_diferenca)


def _contar(lidas: Sequence[Leitura]) -> Contagem:
    classes = [lida.classe for lida in lidas]
    return Contagem(
        len(lidas),
        sum(1 for lida in lidas if lida.z is not None),
        classes.count(MODERADO),
        classes.count(FORA_A),
        classes.count(FORA_B),
    )


def _fora_por_uf(lidos: Sequence[tuple[ParMunicipal, Leitura]]) -> tuple[tuple[str, int], ...]:
    contagem: dict[str, int] = {}
    for par, lida in lidos:
        if lida.classe in (FORA_A, FORA_B):
            contagem[par.uf] = contagem.get(par.uf, 0) + 1
    return tuple((uf, contagem[uf]) for uf in UF_CODES if uf in contagem)


def _ordem(chave: tuple[str, str]) -> tuple[int, str]:
    uf, codigo = chave
    posicao = UF_CODES.index(uf) if uf in UF_CODES else len(UF_CODES)
    return posicao, codigo


def _cenario_json(item: CalibracaoCenario) -> dict[str, object]:
    parte = item.cenario.parte_de_a
    return {
        "chave": item.cenario.chave,
        "rotulo": item.cenario.rotulo,
        "parte_de_a": None if parte is None else _arredondado(float(parte)),
        "nacional": {
            "esperado_a": _arredondado(float(item.nacional.esperado)),
            "real_a": _arredondado(float(item.nacional.real)),
            "residuo": _arredondado(float(item.nacional.residuo)),
            "votos_de_diferenca": item.nacional.votos_de_diferenca,
        },
        "municipios": _contagem_json(item.municipios),
        "quantis_abs_z": {_rotulo(p): _arredondado(valor) for p, valor in item.quantis},
        "limiares_por_fracao": {
            _rotulo(limiar.fracao_alvo): {
                "abs_z": _arredondado(limiar.abs_z),
                "marcados": limiar.marcados,
            }
            for limiar in item.limiares
        },
        "fora_por_uf": dict(item.fora_por_uf),
        "exterior": _contagem_json(item.exterior),
    }


def _contagem_json(contagem: Contagem) -> dict[str, object]:
    return {
        "lugares": contagem.lugares,
        "com_base": contagem.com_base,
        "sem_base": contagem.sem_base,
        "moderados": contagem.moderados,
        "fora_a": contagem.fora_a,
        "fora_b": contagem.fora_b,
        "fracao_acima_do_moderado": _fracao(contagem.acima_do_moderado, contagem.com_base),
        "fracao_moderado": _fracao(contagem.moderados, contagem.com_base),
        "fracao_fora": _fracao(contagem.fora, contagem.com_base),
    }


def _fracao(parte: int, todo: int) -> float | None:
    return None if todo == 0 else _arredondado(parte / todo)


def _rotulo(p: float) -> str:
    return f"{p:g}"


def _arredondado(valor: float) -> float:
    return round(valor, _CASAS)


_DESCRICAO: Final = {
    "eleicao": "Ano, cargo, finalistas (a é o apoiado, como em 2026) e URLs dos zips do TSE.",
    "parametros": "Constantes de mapa_turnos usadas na conta e o método do quantil.",
    "referencia_normal": "P(|Z| > limiar) para Z normal padrão, o z robusto sem caudas.",
    "municipios_pareados": "Lugares, exterior incluído, presentes nos dois turnos.",
    "sem_par": "Lugares presentes num turno só; ficam fora da conta.",
    "melhor_ajuste": "Chave do cenário com o menor |residuo| nacional.",
    "cenarios[].parte_de_a": "Parte dos votos dos eliminados que vai para a; null no proporcional.",
    "cenarios[].nacional": (
        "Brasil e exterior somados: fatia esperada e real de a entre os votos dos finalistas, "
        "residuo = real - esperado e o mesmo resíduo em votos do 2º turno."
    ),
    "cenarios[].municipios": (
        "Municípios do Brasil lidos por UF. com_base tem z (piso de votos e grupo mínimo); "
        "sem_base não tem. As frações dividem por com_base: acima_do_moderado é |z| > "
        "limiar_moderado (moderados + fora), moderado só a faixa do meio e fora |z| > limiar_fora."
    ),
    "cenarios[].quantis_abs_z": "Quantis de |z| nos municípios com base, pela chave da ordem p.",
    "cenarios[].limiares_por_fracao": (
        "Para cada fração alvo, o menor |z| observado tal que |z| > abs_z marque no máximo essa "
        "fração dos municípios com base; marcados é quantos passam."
    ),
    "cenarios[].fora_por_uf": "Municípios fora do esperado (|z| > limiar_fora) por UF.",
    "cenarios[].exterior": "As cidades do exterior (ZZ) lidas como um grupo só, contadas à parte.",
}
