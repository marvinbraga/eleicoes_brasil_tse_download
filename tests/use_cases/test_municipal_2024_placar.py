import asyncio
from datetime import UTC, datetime

from eleicoes.domain.forca_municipal import (
    MunicipalCountsByUf,
    StoredMunicipalResults,
    UfPartyCount,
    UfTotals,
)
from eleicoes.domain.partido_equivalencia import VERSAO_EQUIVALENCIA
from eleicoes.ports.municipal_2024 import (
    AsyncMunicipal2024,
    Municipal2024,
    MunicipalPartido2024,
    TotaisMunicipal2024,
)
from eleicoes.use_cases.municipal_2024_placar import StoredMunicipal2024

_CORTE = datetime(2026, 10, 22, 2, 17)
_IMPORTADO = datetime(2026, 10, 22, 13, 5, tzinfo=UTC)


class _Reader:
    def __init__(self, counts: MunicipalCountsByUf | None) -> None:
        self.counts = counts
        self.years: list[int] = []

    async def load(self, ano: int, uf: str | None) -> StoredMunicipalResults | None:
        del ano, uf
        raise AssertionError("the scoreboard reads only the grouped counts")

    async def party_counts_by_uf(self, ano: int) -> MunicipalCountsByUf | None:
        self.years.append(ano)
        return self.counts


def _counts() -> MunicipalCountsByUf:
    return MunicipalCountsByUf(
        corte=_CORTE,
        importado_em=_IMPORTADO,
        totais=(
            UfTotals("MG", 853, 852, 16469155, 8526),
            UfTotals("AC", 22, 22, 600000, 200),
        ),
        linhas=(
            UfPartyCount("MG", 35, "PMB", 3, 30000, 40),
            UfPartyCount("MG", 65, "PC do B", 1, 5000, 10),
            UfPartyCount("MG", 14, "PTB", 2, 7000, 9),
            UfPartyCount("AC", 35, "PMB", 1, 1000, 2),
            UfPartyCount("AC", 50, "PSOL", 0, 0, 3),
        ),
    )


def _load(counts: MunicipalCountsByUf | None) -> Municipal2024 | None:
    reader = _Reader(counts)
    port: AsyncMunicipal2024 = StoredMunicipal2024(reader)
    loaded = asyncio.run(port.load())
    assert reader.years == [2024]
    return loaded


def test_rows_use_the_2026_number_and_add_a_country_row() -> None:
    loaded = _load(_counts())
    assert loaded is not None
    assert loaded.linhas == (
        MunicipalPartido2024(35, "AC", 1, 1000, 2),
        MunicipalPartido2024(35, "MG", 3, 30000, 40),
        MunicipalPartido2024(35, "BR", 4, 31000, 42),
        MunicipalPartido2024(50, "AC", 0, 0, 3),
        MunicipalPartido2024(50, "BR", 0, 0, 3),
        MunicipalPartido2024(65, "MG", 1, 5000, 10),
        MunicipalPartido2024(65, "BR", 1, 5000, 10),
    )


def test_number_without_counterpart_stays_out_of_rows_but_in_the_totals() -> None:
    loaded = _load(_counts())
    assert loaded is not None
    assert loaded.sem_correspondencia == (14,)
    assert all(item.partido != 14 for item in loaded.linhas)
    assert loaded.totais == (
        TotaisMunicipal2024("AC", 22, 22, 600000, 200),
        TotaisMunicipal2024("MG", 853, 852, 16469155, 8526),
        TotaisMunicipal2024("BR", 875, 874, 17069155, 8726),
    )


def test_metadata_and_no_federal_district() -> None:
    loaded = _load(_counts())
    assert loaded is not None
    assert (loaded.data_corte, loaded.importado_em) == (_CORTE, _IMPORTADO)
    assert loaded.equivalencia_versao == VERSAO_EQUIVALENCIA
    assert all(item.uf != "DF" for item in loaded.linhas)
    assert all(item.uf != "DF" for item in loaded.totais)


def test_reader_without_import_gives_none() -> None:
    assert _load(None) is None
