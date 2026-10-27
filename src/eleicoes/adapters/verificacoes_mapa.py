"""Resume, por município, o relatório de seções e a verificação das urnas para o mapa.

O mapa do 1º × 2º turno pinta dois resultados que nascem seção a seção: quantas seções
ficaram fora do esperado em cada cenário (relatorios/secoes-turnos-{ano}.csv) e quantas
conferem entre boletim, RDV e log (relatorios/integridade-urnas-{ano}-turno-2.csv). Aqui
eles viram contagens por município, já na chave da malha: o código IBGE, ou o código do
TSE para as cidades do exterior, como o mapa as desenha.
"""

import csv
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Final

from eleicoes.domain.mapa import PonteTseIbge
from eleicoes.domain.mapa_turnos import chave_tse

_EXTERIOR: Final = "ZZ"
_FORA: Final = frozenset({"fora_a", "fora_b"})
_PREFIXO_DA_CLASSE: Final = "classe_"
_SEM_BASE: Final = "sem_base"
_SITUACOES: Final = ("confere", "diverge", "sem_rdv", "sem_log", "ilegivel")


def codigo_no_mapa(uf: str, municipio: str, ponte: PonteTseIbge) -> str | None:
    tse = chave_tse(municipio.strip())
    if uf == _EXTERIOR:
        return tse
    return ponte.municipio_por_tse.get(tse)


def secoes_por_municipio(
    linhas: Iterable[Mapping[str, str]], ponte: PonteTseIbge
) -> dict[str, dict[str, object]]:
    """Seções com z e seções fora do esperado (|z| > 3,5) de cada cenário."""
    com_z: dict[str, int] = {}
    fora: dict[str, dict[str, int]] = {}
    for linha in linhas:
        codigo = codigo_no_mapa(linha.get("uf", ""), linha.get("municipio", ""), ponte)
        if codigo is None:
            continue
        cenarios = [chave for chave in linha if chave.startswith(_PREFIXO_DA_CLASSE)]
        avaliada = any(linha[chave] not in ("", _SEM_BASE) for chave in cenarios)
        com_z[codigo] = com_z.get(codigo, 0) + avaliada
        do_lugar = fora.setdefault(codigo, {})
        for chave in cenarios:
            cenario = chave[len(_PREFIXO_DA_CLASSE) :]
            do_lugar[cenario] = do_lugar.get(cenario, 0) + (linha[chave] in _FORA)
    return {codigo: {"comZ": com_z[codigo], "fora": fora[codigo]} for codigo in com_z}


def integridade_por_municipio(
    linhas: Iterable[Mapping[str, str]], ponte: PonteTseIbge
) -> dict[str, list[int]]:
    """Seções por situação, na ordem de _SITUACOES."""
    found: dict[str, list[int]] = {}
    for linha in linhas:
        codigo = codigo_no_mapa(linha.get("uf", ""), linha.get("municipio", ""), ponte)
        situacao = linha.get("situacao", "")
        if codigo is None or situacao not in _SITUACOES:
            continue
        contagem = found.setdefault(codigo, [0] * len(_SITUACOES))
        contagem[_SITUACOES.index(situacao)] += 1
    return found


def ler_verificacoes(
    secoes: Path, integridade: Path, ponte: PonteTseIbge
) -> dict[str, object] | None:
    """None quando nenhum dos dois arquivos existe; cada parte falta sozinha."""
    found: dict[str, object] = {}
    if secoes.is_file():
        with secoes.open(encoding="utf-8-sig", newline="") as arquivo:
            found["secoes"] = secoes_por_municipio(csv.DictReader(arquivo), ponte)
        found["secoesEm"] = _gravado_em(secoes)
    if integridade.is_file():
        with integridade.open(encoding="utf-8", newline="") as arquivo:
            found["integridade"] = integridade_por_municipio(csv.DictReader(arquivo), ponte)
        found["integridadeEm"] = _gravado_em(integridade)
        found["situacoes"] = list(_SITUACOES)
    return found or None


def _gravado_em(caminho: Path) -> str:
    return datetime.fromtimestamp(caminho.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
