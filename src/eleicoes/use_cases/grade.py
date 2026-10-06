"""Builds a party-share grid from places the consultation already grouped."""

from eleicoes.domain.boletim_consulta import PoderPartido
from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.grade import (
    CelulaGrade,
    GradeDePoder,
    LinhaGrade,
    LugarVotos,
    ordered_parties,
    place_sort_key,
)


class BuildPartyShareGrid:
    def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        nivel: str,
        lugares: tuple[LugarVotos, ...],
    ) -> GradeDePoder:
        columns = ordered_parties(_totals(lugares))
        rows = tuple(sorted((_linha(lugar, columns) for lugar in lugares), key=_row_key))
        return GradeDePoder(ano, turno, uf, cargo, nivel, columns, rows)


def _totals(lugares: tuple[LugarVotos, ...]) -> dict[int, int]:
    totals: dict[int, int] = {}
    for lugar in lugares:
        _add_place(totals, lugar)
    return totals


def _add_place(totals: dict[int, int], lugar: LugarVotos) -> None:
    seen: set[int] = set()
    for line in lugar.linhas:
        if line.partido in seen:
            raise InvalidBoletimConsultaError("partido")
        seen.add(line.partido)
        totals[line.partido] = totals.get(line.partido, 0) + line.votos


def _linha(lugar: LugarVotos, columns: tuple[int, ...]) -> LinhaGrade:
    by_party = {line.partido: line for line in lugar.linhas}
    cells = tuple(_celula(party, by_party.get(party), lugar.comparecimento) for party in columns)
    return LinhaGrade(lugar.codigo, lugar.nome, lugar.comparecimento, cells)


def _celula(party: int, line: PoderPartido | None, comparecimento: int) -> CelulaGrade:
    if line is None:
        return CelulaGrade(party, 0, 0, comparecimento)
    return CelulaGrade(party, line.votos_nominais, line.votos_legenda, comparecimento)


def _row_key(linha: LinhaGrade) -> tuple[str, str]:
    return place_sort_key(linha.nome, linha.codigo)
