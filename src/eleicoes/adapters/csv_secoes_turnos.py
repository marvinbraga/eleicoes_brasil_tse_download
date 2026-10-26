"""CSV do 1º × 2º turno seção por seção: uma linha por seção pareada."""

import csv
import io
from typing import Final

from eleicoes.domain.anomalia_secao import ALERTAS, AnaliseSecoes, SecaoTurnos
from eleicoes.domain.mapa_turnos import Cenario, Leitura

_FIXAS: Final = (
    "uf",
    "municipio",
    "nome_municipio",
    "zona",
    "secao",
    "aptos_1",
    "aptos_2",
    "complemento_1",
    "complemento_2",
    "a_1",
    "b_1",
    "eliminados_1",
    "branco_1",
    "nulo_1",
    "cedulas_1",
    "a_2",
    "b_2",
    "outros_2",
    "branco_2",
    "nulo_2",
    "cedulas_2",
    "real_a",
    "comparavel",
    "grupo",
    "verificacoes",
)
_POR_CENARIO: Final = ("esperado_a", "residuo", "votos_de_diferenca", "z", "classe")
_CASAS: Final = 6


def csv_das_secoes(analise: AnaliseSecoes) -> str:
    saida = io.StringIO()
    escritor = csv.writer(saida, lineterminator="\n")
    escritor.writerow(_cabecalho(analise.cenarios))
    for secao in analise.secoes:
        escritor.writerow(_linha(secao))
    return saida.getvalue()


def _cabecalho(cenarios: tuple[Cenario, ...]) -> list[str]:
    colunas = list(_FIXAS)
    for cenario in cenarios:
        colunas.extend(f"{coluna}_{cenario.chave}" for coluna in _POR_CENARIO)
    return colunas


def _linha(secao: SecaoTurnos) -> list[object]:
    um = secao.primeiro
    dois = secao.segundo
    real = secao.leituras[0].real if secao.leituras else None
    linha: list[object] = [
        secao.uf,
        secao.municipio,
        secao.nome,
        secao.zona,
        secao.secao,
        *secao.aptos,
        *secao.complemento,
        um.a,
        um.b,
        um.outros,
        um.branco,
        um.nulo,
        um.cedulas,
        dois.a,
        dois.b,
        dois.outros,
        dois.branco,
        dois.nulo,
        dois.cedulas,
        "" if real is None else round(float(real), _CASAS),
        int(secao.comparavel),
        secao.grupo,
        ";".join(alerta for alerta in ALERTAS if alerta in secao.alertas),
    ]
    for leitura in secao.leituras:
        linha.extend(_leitura(leitura))
    return linha


def _leitura(leitura: Leitura) -> list[object]:
    return [
        round(float(leitura.esperado), _CASAS),
        round(float(leitura.residuo), _CASAS),
        leitura.votos_de_diferenca,
        "" if leitura.z is None else round(leitura.z, 4),
        leitura.classe,
    ]
