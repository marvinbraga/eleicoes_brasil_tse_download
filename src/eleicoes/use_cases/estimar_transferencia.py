"""Estima pelos dados a transferência de votos do 1º para o 2º turno de presidente.

Só lê o banco: o 1º turno vem do relatório guardado e o 2º dos boletins.
"""

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Final

from dotenv import load_dotenv

from eleicoes.domain.errors import ElectionError, InvalidElectionYearError
from eleicoes.domain.mapa_turnos import FinalistsMissingError, finalistas
from eleicoes.domain.percentual import format_integer
from eleicoes.domain.presidente_governador import MunicipalPlace
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.transferencia import (
    BRANCO_NULO,
    MINIMO_DE_MUNICIPIOS,
    NIVEL,
    REAMOSTRAS,
    SEMENTE,
    EstimativaDeTransferencia,
    Grupos,
    InvalidConfidenceLevelError,
    InvalidResampleCountError,
    Observacao,
    Taxa,
    estimar_por_uf,
    grupos_do_primeiro,
    observacoes,
)
from eleicoes.domain.values import ElectionYear

Collect = Callable[[int, int], tuple[MunicipalPlace, ...]]

APOIADO: Final = 22
RAZAO_MINIMA: Final = 0.5
RAZAO_MAXIMA: Final = 1.5
_LARGURA_GRUPO: Final = 12
_LARGURA_CEDULAS: Final = 11
_LARGURA_TAXA: Final = 22
_NOMES_LISTADOS: Final = 5


class FirstRoundMissingError(ElectionError):
    def __init__(self, ano: int) -> None:
        super().__init__(f"first round of {ano} is not stored")


def main(
    argv: Sequence[str] | None = None,
    *,
    primeiro: Collect | None = None,
    segundo: Collect | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        ElectionYear(args.ano)
        antes = (primeiro or _production_first)(args.ano, 1)
        depois = (segundo or _production_second)(args.ano, 2)
        text = relatorio(antes, depois, args)
    except ElectionError as error:
        print(_failure(error), file=sys.stderr)
        return EXIT_FAILURE
    print(text)
    return EXIT_SUCCESS


def relatorio(
    primeiro: Sequence[MunicipalPlace],
    segundo: Sequence[MunicipalPlace],
    args: argparse.Namespace,
) -> str:
    a, b = finalistas(segundo, args.apoiado)
    grupos = grupos_do_primeiro(primeiro, a, b)
    lista = observacoes(primeiro, segundo, grupos)
    estimadas, puladas = estimar_por_uf(
        lista,
        grupos,
        minimo=args.minimo,
        reamostras=args.reamostras,
        nivel=args.nivel,
        semente=args.semente,
    )
    partes = [_cabecalho(args, grupos)]
    for estimativa in estimadas:
        grupo = tuple(obs for obs in lista if obs.uf == estimativa.uf)
        partes.append(tabela(estimativa, grupo))
    if puladas:
        partes.append(
            f"Sem estimativa (menos de {args.minimo} municípios comparáveis): {', '.join(puladas)}."
        )
    if not estimadas and not puladas:
        partes.append("Nenhum município aparece nos dois turnos.")
    return "\n\n".join(partes)


def tabela(estimativa: EstimativaDeTransferencia, grupo: Sequence[Observacao] = ()) -> str:
    a, b = estimativa.a, estimativa.b
    aviso = " (amostra pequena: intervalos instáveis)" if estimativa.amostra_pequena else ""
    linhas = [
        f"{estimativa.uf}: {estimativa.municipios} municípios{aviso}. "
        f"R² ponderado da fatia do {a}: {_decimal(estimativa.r2_de_a, 3)}. "
        f"RMSE: {_decimal(estimativa.rmse * 100, 2)} p.p.",
        _colunas("Do 1º turno", "Cédulas", f"→ {a}", f"→ {b}", "→ branco+nulo"),
    ]
    for linha in estimativa.linhas:
        linhas.append(
            _colunas(
                _rotulo(linha.grupo),
                format_integer(linha.votos),
                *(_taxa(taxa) for taxa in linha.taxas),
            )
        )
    if estimativa.ausentes:
        nomes = ", ".join(_rotulo(chave) for chave in estimativa.ausentes)
        linhas.append(f"Sem votos na UF: {nomes}.")
    linhas.append(
        f"Dos votos dos eliminados que foram a um finalista, para o {a}: "
        f"{_taxa(estimativa.parte_de_a)}."
    )
    linhas.extend(_alerta_de_cedulas(grupo))
    return "\n".join(linhas)


def _cabecalho(args: argparse.Namespace, grupos: Grupos) -> str:
    destacados = ", ".join(str(numero) for numero in grupos.destacados) or "nenhum"
    nivel = _decimal(args.nivel * 100, 0)
    return "\n".join(
        (
            f"Transferência estimada do 1º para o 2º turno de presidente, {args.ano}.",
            f"Finalistas: {grupos.a} (A) e {grupos.b} (B). "
            f"Eliminados com pelo menos 1% no país: {destacados}; os demais vão em outros.",
            f"Regressão ecológica por UF, com taxas em [0, 1] e linhas somando 100%. "
            f"Intervalos de {nivel}% por bootstrap dos municípios "
            f"({args.reamostras} reamostras, semente {args.semente}).",
            "Suposição: compara fatias das cédulas de cada turno. Quem votou num turno "
            "e faltou no outro, ou só votou no 2º, não entra no modelo.",
            "É uma média por município, não o voto de cada eleitor, e não prova irregularidade.",
        )
    )


def _alerta_de_cedulas(grupo: Sequence[Observacao]) -> list[str]:
    estranhos = [
        obs
        for obs in grupo
        if obs.cedulas_primeiro > 0
        and not RAZAO_MINIMA <= obs.cedulas_segundo / obs.cedulas_primeiro <= RAZAO_MAXIMA
    ]
    if not estranhos:
        return []
    nomes = ", ".join(obs.nome for obs in estranhos[:_NOMES_LISTADOS])
    resto = len(estranhos) - _NOMES_LISTADOS
    if resto > 0:
        nomes += f" e mais {resto}"
    faixa = f"{_decimal(RAZAO_MINIMA * 100, 0)}% a {_decimal(RAZAO_MAXIMA * 100, 0)}%"
    return [
        f"Atenção: {len(estranhos)} municípios com cédulas do 2º turno fora de {faixa} "
        f"das do 1º (apuração parcial?): {nomes}."
    ]


def _colunas(grupo: str, cedulas: str, *taxas: str) -> str:
    return (
        f"  {grupo:<{_LARGURA_GRUPO}}{cedulas:>{_LARGURA_CEDULAS}}  "
        + "".join(f"{taxa:<{_LARGURA_TAXA}}" for taxa in taxas).rstrip()
    )


def _rotulo(chave: str) -> str:
    return "branco+nulo" if chave == BRANCO_NULO else chave


def _taxa(taxa: Taxa) -> str:
    return (
        f"{_decimal(taxa.estimada * 100)}% "
        f"({_decimal(taxa.inferior * 100)}–{_decimal(taxa.superior * 100)})"
    )


def _decimal(valor: float, casas: int = 1) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estima pelos dados a transferência de votos entre os turnos de presidente.",
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--apoiado", type=int, default=APOIADO)
    parser.add_argument("--reamostras", type=int, default=REAMOSTRAS)
    parser.add_argument("--nivel", type=float, default=NIVEL)
    parser.add_argument("--semente", type=int, default=SEMENTE)
    parser.add_argument("--minimo", type=int, default=MINIMO_DE_MUNICIPIOS)
    return parser


def _failure(error: ElectionError) -> str:
    if isinstance(error, InvalidElectionYearError):
        return "Ano inválido. Informe um ano entre 1994 e 2100."
    if isinstance(error, FirstRoundMissingError):
        return "O 1º turno deste ano não está guardado no banco."
    if isinstance(error, FinalistsMissingError):
        return "O 2º turno de presidente ainda não tem votos importados."
    if isinstance(error, InvalidConfidenceLevelError):
        return "Nível de confiança inválido. Informe um valor entre 0 e 1, como 0.9."
    if isinstance(error, InvalidResampleCountError):
        return "Número de reamostras inválido. Informe 0 ou mais."
    return str(error)


def _production_first(ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
    from eleicoes.composition.presidente_governador import build_cross_report_store

    stored = build_cross_report_store(_environment()).load(ano, turno)
    if stored is None:
        raise FirstRoundMissingError(ano)
    return stored.places


def _production_second(ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
    from eleicoes.composition.boletim import build_boletim_reader
    from eleicoes.composition.grade import build_municipality_names
    from eleicoes.use_cases.presidente_governador import collect_places

    env = _environment()
    reader = build_boletim_reader(env)
    names = build_municipality_names(env)
    try:
        return collect_places(reader, names, ano, turno)
    finally:
        reader.close()
        names.close()


def _environment() -> Mapping[str, str]:
    load_dotenv()
    return os.environ
