"""Implementa a porta do Placar: contagens de 2024 já no número de partido de 2026."""

from collections.abc import Iterable
from typing import Final

from eleicoes.domain.forca_municipal import UfPartyCount, UfTotals
from eleicoes.domain.partido_equivalencia import VERSAO_EQUIVALENCIA, equivalente_2026
from eleicoes.ports.municipais import AsyncMunicipalResultsReader
from eleicoes.ports.municipal_2024 import Municipal2024, MunicipalPartido2024, TotaisMunicipal2024
from eleicoes.use_cases.apresentar_municipais import MUNICIPAL_REPORT_YEAR

PAIS: Final = "BR"
_Counts = tuple[int, int, int]


class StoredMunicipal2024:
    def __init__(self, reader: AsyncMunicipalResultsReader) -> None:
        self._reader = reader

    async def load(self) -> Municipal2024 | None:
        counts = await self._reader.party_counts_by_uf(MUNICIPAL_REPORT_YEAR)
        if counts is None:
            return None
        linhas, sem_correspondencia = _rows(counts.linhas)
        return Municipal2024(
            data_corte=counts.corte,
            importado_em=counts.importado_em,
            equivalencia_versao=VERSAO_EQUIVALENCIA,
            totais=_totals(counts.totais),
            linhas=linhas,
            sem_correspondencia=sem_correspondencia,
        )


def _rows(
    counts: Iterable[UfPartyCount],
) -> tuple[tuple[MunicipalPartido2024, ...], tuple[int, ...]]:
    summed: dict[tuple[int, str], _Counts] = {}
    unmatched: set[int] = set()
    for item in counts:
        numero = equivalente_2026(item.partido, item.sigla).numero_2026
        if numero is None:
            unmatched.add(item.partido)
            continue
        values = (item.prefeitos, item.eleitorado, item.vereadores)
        for key in ((numero, item.uf), (numero, PAIS)):
            summed[key] = _add(summed.get(key, (0, 0, 0)), values)
    rows = tuple(
        MunicipalPartido2024(partido, uf, *summed[(partido, uf)])
        for partido, uf in sorted(summed, key=_row_order)
    )
    return rows, tuple(sorted(unmatched))


def _totals(totais: Iterable[UfTotals]) -> tuple[TotaisMunicipal2024, ...]:
    by_uf = sorted(
        (
            TotaisMunicipal2024(
                item.uf, item.municipios, item.com_prefeito, item.eleitorado, item.vereadores
            )
            for item in totais
        ),
        key=lambda item: item.uf,
    )
    pais = TotaisMunicipal2024(
        PAIS,
        sum(item.municipios for item in by_uf),
        sum(item.com_prefeito for item in by_uf),
        sum(item.eleitorado for item in by_uf),
        sum(item.vereadores for item in by_uf),
    )
    return (*by_uf, pais)


def _add(left: _Counts, right: _Counts) -> _Counts:
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def _row_order(key: tuple[int, str]) -> tuple[int, bool, str]:
    partido, uf = key
    return (partido, uf == PAIS, uf)
