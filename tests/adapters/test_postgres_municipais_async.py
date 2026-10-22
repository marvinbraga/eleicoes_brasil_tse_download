"""AsyncPostgresMunicipalReader against a scripted async cursor. No database socket."""

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from eleicoes.adapters.postgres_municipais_async import AsyncPostgresMunicipalReader
from eleicoes.domain.errors import StoredReadError
from eleicoes.domain.forca_municipal import (
    MunicipalCountsByUf,
    MunicipalTotals,
    PartyCouncil,
    PartyMayors,
    StoredCouncil,
    StoredMayor,
    StoredMunicipality,
    StoredMunicipalResults,
    UfPartyCount,
    UfTotals,
)

_CORTE = datetime(2026, 10, 22, 2, 17)
_IMPORTADO = datetime(2026, 10, 22, 13, 5, tzinfo=UTC)
Rows = tuple[tuple[object, ...], ...]


class _Script:
    def __init__(self, *batches: Rows) -> None:
        self.batches = list(batches)
        self.queries: list[tuple[str, object]] = []
        self.transactions = 0

    def cursor(self) -> "_Cursor":
        return _Cursor(self)

    def transaction(self) -> "_Gate":
        self.transactions += 1
        return _Gate()


class _Gate:
    async def __aenter__(self) -> "_Gate":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


class _Cursor:
    def __init__(self, script: _Script) -> None:
        self._script = script
        self._rows: Rows = ()

    async def execute(self, query: str, params: object = None) -> None:
        self._script.queries.append((query, params))
        self._rows = self._script.batches.pop(0)

    async def fetchall(self) -> Rows:
        return self._rows

    async def __aenter__(self) -> "_Cursor":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


def _national() -> _Script:
    return _Script(
        ((_CORTE, _IMPORTADO),),
        ((5569, 5568, 1, 47, Decimal(155912680), Decimal(58435)),),
        ((Decimal(58435), 0),),
        ((55, "PSD", 887, Decimal(12345678)),),
        ((55, "PSD", 6600, 3100),),
    )


def _load(script: _Script, uf: str | None) -> StoredMunicipalResults | None:
    return asyncio.run(AsyncPostgresMunicipalReader(script).load(2024, uf))


def test_national_scope_binds_null_uf_and_converts_decimals() -> None:
    script = _national()
    stored = _load(script, None)
    assert [params for _sql, params in script.queries] == [
        (2024,),
        (2024, None, None),
        (2024, 2024, None, None),
        (2024, None, None),
        (2024, None, None),
    ]
    assert script.transactions == 1
    assert stored == StoredMunicipalResults(
        ano=2024,
        corte=_CORTE,
        importado_em=_IMPORTADO,
        totais=MunicipalTotals(5569, 5568, 1, 47, 155912680, 58435, 58435, 0),
        prefeitos=(PartyMayors(55, "PSD", 887, 12345678),),
        vereadores=(PartyCouncil(55, "PSD", 6600, 3100),),
        municipios=(),
    )


def test_uf_scope_binds_the_uf_and_reads_the_municipalities() -> None:
    script = _Script(
        ((_CORTE, _IMPORTADO),),
        ((2, 1, 1, 1, Decimal(21000), Decimal(18)),),
        ((Decimal(4), 1),),
        ((22, "PL", 1, Decimal(12000)),),
        ((22, "PL", Decimal(4), 1),),
        (
            ("MG", "45616", "GUAPÉ", 12000, 22, "PL", "DR PEDRO", 1, True, date(2025, 7, 6)),
            ("MG", "48313", "MERCÊS", 9000, None, None, None, None, False, None),
        ),
        (("45616", 22, "PL", 3), ("45616", 13, "PT", 1)),
    )
    stored = _load(script, "MG")
    assert [params for _sql, params in script.queries] == [
        (2024,),
        (2024, "MG", "MG"),
        (2024, 2024, "MG", "MG"),
        (2024, "MG", "MG"),
        (2024, "MG", "MG"),
        (2024, "MG"),
        (2024, "MG"),
    ]
    assert stored is not None
    assert stored.municipios == (
        StoredMunicipality(
            "MG",
            "45616",
            "GUAPÉ",
            12000,
            StoredMayor(22, "PL", "DR PEDRO", 1, True, date(2025, 7, 6)),
            (StoredCouncil(22, "PL", 3), StoredCouncil(13, "PT", 1)),
        ),
        StoredMunicipality("MG", "48313", "MERCÊS", 9000, None, ()),
    )


def test_missing_load_row_is_none() -> None:
    script = _Script(())
    assert _load(script, None) is None
    assert len(script.queries) == 1


@pytest.mark.parametrize(
    "totais",
    [
        ((5569, 5568, 1, 47, Decimal("1.5"), 0),),
        ((5569, 5568, 1, 47, "x", 0),),
        ((True, 5568, 1, 47, 0, 0),),
        (),
    ],
)
def test_unexpected_values_are_a_stored_read_error(totais: Rows) -> None:
    script = _Script(((_CORTE, _IMPORTADO),), totais, ((0, 0),), (), ())
    with pytest.raises(StoredReadError):
        _load(script, None)


def test_load_row_without_datetimes_is_a_stored_read_error() -> None:
    script = _Script((("22/10/2026", _IMPORTADO),), ((0, 0, 0, 0, 0, 0),), ((0, 0),), (), ())
    with pytest.raises(StoredReadError):
        _load(script, None)


def test_mayor_with_a_bad_date_is_a_stored_read_error() -> None:
    script = _Script(
        ((_CORTE, _IMPORTADO),),
        ((1, 1, 0, 0, 0, 0),),
        ((0, 0),),
        (),
        (),
        (("MG", "1", "X", 1, 22, "PL", "A", 1, True, "2025-07-06"),),
        (),
    )
    with pytest.raises(StoredReadError):
        _load(script, "MG")


def _counts(script: _Script) -> MunicipalCountsByUf | None:
    return asyncio.run(AsyncPostgresMunicipalReader(script).party_counts_by_uf(2024))


def test_counts_by_uf_bind_only_the_year_and_join_mayors_with_councillors() -> None:
    script = _Script(
        ((_CORTE, _IMPORTADO),),
        (("MG", 853, 852, Decimal(16469155)), ("AC", 22, 22, Decimal(600000))),
        (("MG", Decimal(8526)),),
        (("MG", 35, "PMB", 3, Decimal(30000)),),
        (("MG", 35, "PMB", Decimal(40)), ("AC", 50, "PSOL", Decimal(3))),
    )
    counts = _counts(script)
    assert [params for _sql, params in script.queries] == [(2024,)] * 5
    assert script.transactions == 1
    assert counts == MunicipalCountsByUf(
        corte=_CORTE,
        importado_em=_IMPORTADO,
        totais=(UfTotals("AC", 22, 22, 600000, 0), UfTotals("MG", 853, 852, 16469155, 8526)),
        linhas=(
            UfPartyCount("AC", 50, "PSOL", 0, 0, 3),
            UfPartyCount("MG", 35, "PMB", 3, 30000, 40),
        ),
    )


def test_counts_by_uf_without_import_is_none() -> None:
    script = _Script(())
    assert _counts(script) is None
    assert len(script.queries) == 1
