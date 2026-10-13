"""Async adapters against a scripted cursor. No database socket."""

import asyncio
from datetime import UTC, datetime

import psycopg
import pytest

from eleicoes.adapters.postgres_boletim_consulta import _PARTY_POWER, _TOTALS
from eleicoes.adapters.postgres_boletim_consulta_async import AsyncPostgresBoletimReader
from eleicoes.adapters.postgres_municipio_async import AsyncPostgresMunicipalityNames
from eleicoes.adapters.postgres_relatorio_poder_async import AsyncPostgresPowerReportStore
from eleicoes.adapters.postgres_relatorio_presidente_governador_async import (
    AsyncPostgresPresidentGovernorStore,
)
from eleicoes.domain.errors import ElectionError, InvalidNivelError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.domain.stored_grade import StoredCell

_MOMENT = datetime(2026, 10, 8, 14, 30, tzinfo=UTC)


class _Script:
    def __init__(self) -> None:
        self.batches: list[tuple[tuple[object, ...], ...]] = []
        self.queries: list[tuple[str, object]] = []
        self.fail: BaseException | None = None

    def push(self, *rows: tuple[object, ...]) -> None:
        self.batches.append(rows)

    def cursor(self) -> "_Cursor":
        return _Cursor(self)

    def transaction(self) -> "_Gate":
        return _Gate()


class _Gate:
    async def __aenter__(self) -> "_Gate":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


class _Cursor:
    def __init__(self, script: _Script) -> None:
        self._script = script
        self._rows: tuple[tuple[object, ...], ...] = ()

    async def execute(self, query: str, params: object = None) -> None:
        self._script.queries.append((query, params))
        if self._script.fail is not None:
            raise self._script.fail
        self._rows = self._script.batches.pop(0)

    async def fetchall(self) -> tuple[tuple[object, ...], ...]:
        return self._rows

    async def __aenter__(self) -> "_Cursor":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


class _Connection:
    def __init__(self, script: _Script) -> None:
        self._script = script

    def cursor(self) -> _Cursor:
        return self._script.cursor()

    def transaction(self) -> _Gate:
        return self._script.transaction()


def test_reader_maps_the_same_sql_as_the_sync_adapter() -> None:
    script = _Script()
    script.push(("nominal", 13, 13, 8))
    script.push((1120, 8, 20))
    script.push((1120, 8, 3, 20))
    script.push((1120, 13, 5, 1, 20))
    script.push((1120, 20, 16))
    script.push((1120, 1, 0, 20))
    script.push((1120, 13, 13, 8, None, None, None, 20))
    script.push(("presidente", 1, "nominal", 13, 13, 8))
    script.push((1, 8, 20))
    script.push((1120, 1, 2, 20, 8))
    script.push((1120, 13, 8))
    script.push((1120, 1))
    script.push(("se",))
    reader = AsyncPostgresBoletimReader(_Connection(script))

    async def read() -> tuple[object, ...]:
        return (
            await reader.totals(2026, 1, "SE", "presidente"),
            await reader.municipalities(2026, 1, "SE", "presidente", 13),
            await reader.comparison(2026, 1, "SE", "presidente", 13, 22, "municipio"),
            await reader.party_power(2026, 1, ("SE",), "presidente", "municipio"),
            await reader.participation(2026, 1, "SE", "presidente", "municipio"),
            await reader.blank_and_null(2026, 1, "SE", "presidente", "municipio"),
            await reader.leading_candidate(2026, 1, "SE", "presidente", "municipio"),
            await reader.section_lines(2026, 1, "SE", 1120, 1, 2),
            await reader.zones(2026, 1, "SE", 1120, "presidente", 13),
            await reader.section_projections(2026, 1, "SE", "presidente"),
            await reader.nominal_projections(2026, 1, "SE", "presidente"),
            await reader.blank_projections(2026, 1, "SE", "presidente"),
            await reader.present_ufs(2026, 1, "presidente"),
        )

    rows = asyncio.run(read())
    assert rows[0][0].quantidade == 8
    assert rows[1][0].municipio == 1120
    assert rows[2][0].votos_primeiro == 8
    assert rows[3][0].partido == 13
    assert rows[4][0].comparecimento == 16
    assert rows[5][0].branco == 1
    assert rows[6][0].numero == 13
    assert rows[7][0].cargo == "presidente"
    assert rows[8][0].zona == 1
    assert rows[9][0].secao == 2
    assert rows[10][0].numero == 13
    assert rows[11][0].quantidade == 1
    assert rows[12] == ("SE",)
    assert script.queries[0][0] == _TOTALS
    assert script.queries[3][0] == _PARTY_POWER["municipio"]
    assert script.queries[3][1] == (2026, 1, ["SE"], "presidente", 2026, 1, ["SE"], "presidente")


def test_unknown_level_does_not_query() -> None:
    script = _Script()
    reader = AsyncPostgresBoletimReader(_Connection(script))
    with pytest.raises(InvalidNivelError):
        asyncio.run(reader.comparison(2026, 1, "SE", "presidente", 13, 22, "bairro"))
    assert script.queries == []


def test_driver_errors_become_election_errors() -> None:
    script = _Script()
    script.fail = psycopg.Error("down")
    reader = AsyncPostgresBoletimReader(_Connection(script))
    with pytest.raises(ElectionError) as caught:
        asyncio.run(reader.totals(2026, 1, "SE", "presidente"))
    assert isinstance(caught.value.__cause__, psycopg.Error)


def test_municipality_names_use_the_uf_code() -> None:
    script = _Script()
    script.push((1120, "Aracaju"))
    names = AsyncPostgresMunicipalityNames(_Connection(script))
    found = asyncio.run(names.names("se"))
    assert found == {1120: "Aracaju"}
    assert script.queries[0][1] == ("SE",)


def test_power_store_loads_and_replaces_cells() -> None:
    script = _Script()
    script.push(("uf", "SE", "Sergipe", 20, 13, 5, 1, _MOMENT))
    store = AsyncPostgresPowerReportStore(_Connection(script))
    loaded = asyncio.run(store.load(2026, 1, "presidente"))
    assert loaded is not None
    assert loaded.cells[0].codigo == "SE"
    assert loaded.gerado_em == _MOMENT
    cell = StoredCell("municipio", "1120", "Aracaju", 20, 13, 5, 1)
    script.push((_MOMENT,))
    script.push()
    script.push()
    moment = asyncio.run(store.save(2026, 1, "presidente", (cell,)))
    assert moment == _MOMENT


def test_power_store_load_miss_and_broken_clock() -> None:
    script = _Script()
    script.push()
    store = AsyncPostgresPowerReportStore(_Connection(script))
    assert asyncio.run(store.load(2026, 1, "presidente")) is None
    script.push()
    with pytest.raises(ElectionError):
        asyncio.run(store.save(2026, 1, "presidente", ()))


def test_cross_store_round_trip_with_and_without_governor() -> None:
    script = _Script()
    script.push()
    store = AsyncPostgresPresidentGovernorStore(_Connection(script))
    assert asyncio.run(store.load(2026, 1)) is None
    script.push((_MOMENT,))
    script.push(("SE", "1120", "Aracaju", "presidente", 13, 5, 1))
    script.push(("SE", "1120", "presidente", 1, 0))
    loaded = asyncio.run(store.load(2026, 1))
    assert loaded is not None
    assert loaded.places[0].nome == "Aracaju"
    assert loaded.places[0].governador is None
    president = CargoTally((PartyTally(13, 5, 1),), 1, 0)
    governor = CargoTally((PartyTally(22, 4, 0),), 0, 1)
    place = MunicipalPlace("SE", "1120", "Aracaju", president, governor)
    script.push((_MOMENT,))
    for _query in range(6):
        script.push()
    moment = asyncio.run(store.save(2026, 1, (place,)))
    assert moment == _MOMENT
    cargos = [
        params[5]
        for _sql, params in script.queries
        if isinstance(params, tuple) and len(params) == 9
    ]
    assert cargos == ["presidente", "governador"]
    solo = MunicipalPlace("SE", "1120", "Aracaju", president, None)
    script.push((_MOMENT,))
    for _query in range(4):
        script.push()
    assert asyncio.run(store.save(2026, 1, (solo,))) == _MOMENT
