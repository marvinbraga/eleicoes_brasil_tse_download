"""CSV de "De onde vieram os votos": uma linha por município comparado, com todas as contas."""

import csv
import io
from typing import Final

from eleicoes.domain.origem_votos import MunicipioOrigem, OrigemDosVotos

_COLUNAS: Final = (
    "uf",
    "municipio",
    "nome_municipio",
    "aptos_1",
    "comparecimento_1",
    "a_1",
    "b_1",
    "eliminados_1",
    "branco_nulo_1",
    "cedulas_1",
    "aptos_2",
    "comparecimento_2",
    "a_2",
    "b_2",
    "outros_2",
    "branco_nulo_2",
    "cedulas_2",
    "delta_a",
    "delta_b",
    "delta_branco_nulo",
    "delta_comparecimento",
    "delta_aptos",
    "fontes",
    "residuo",
    "virada_pp",
)
_CASAS: Final = 6


def csv_da_origem(origem: OrigemDosVotos) -> str:
    """`a` e `b` são os finalistas da análise, na ordem do cabeçalho de comentário."""
    saida = io.StringIO()
    saida.write(f"# a = {origem.a}; b = {origem.b}\n")
    escritor = csv.writer(saida, lineterminator="\n")
    escritor.writerow(_COLUNAS)
    for municipio in origem.municipios:
        escritor.writerow(_linha(municipio))
    return saida.getvalue()


def _linha(municipio: MunicipioOrigem) -> tuple[object, ...]:
    b = municipio.balanco
    um, dois = b.primeiro, b.segundo
    virada = "" if b.virada is None else f"{float(b.virada) * 100:.{_CASAS}f}"
    return (
        municipio.uf,
        municipio.codigo,
        municipio.nome,
        um.aptos,
        um.comparecimento,
        um.a,
        um.b,
        um.outros,
        um.branco_nulo,
        um.cedulas,
        dois.aptos,
        dois.comparecimento,
        dois.a,
        dois.b,
        dois.outros,
        dois.branco_nulo,
        dois.cedulas,
        b.delta_a,
        b.delta_b,
        b.delta_branco_nulo,
        b.delta_comparecimento,
        b.delta_aptos,
        b.fontes,
        b.residuo,
        virada,
    )
