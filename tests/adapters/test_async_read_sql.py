"""Async adapters against a scripted cursor or SQLite. No database socket."""

import asyncio
from datetime import datetime
from types import SimpleNamespace

import psycopg
import pytest
from tests.adapters.orm_fakes import ScriptedSession, SyncSessionBridge, memory_sessions

from eleicoes.adapters.orm.models import Base, CorrespondenceSection
from eleicoes.adapters.postgres_boletim_consulta import _PARTY_POWER, _SECTION_VOTES, _TOTALS
from eleicoes.adapters.postgres_boletim_consulta_async import AsyncPostgresBoletimReader
from eleicoes.adapters.postgres_municipio_async import AsyncPostgresMunicipalityNames
from eleicoes.adapters.postgres_relatorio_poder_async import AsyncPostgresPowerReportStore
from eleicoes.adapters.postgres_relatorio_presidente_governador_async import (
    AsyncPostgresPresidentGovernorStore,
)
from eleicoes.domain.errors import ElectionError, InvalidNivelError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.ports.relatorio_poder import StoredReport
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport


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


def test_section_votes_use_the_sync_sql_and_grouping() -> None:
    script = _Script()
    script.push((1120, 1, 2, 300, 0, 3, 4, 13, 8), (1120, 1, 2, 300, 0, 3, 4, 22, 9))
    reader = AsyncPostgresBoletimReader(_Connection(script))
    secoes = asyncio.run(reader.section_votes(2026, 2, "SE", "presidente"))
    assert script.queries[0][0] == _SECTION_VOTES
    assert script.queries[0][1] == (2026, 2, "SE", "presidente")
    assert secoes[0].nominais == ((13, 8), (22, 9))


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
    sessions = memory_sessions()
    writer = sessions()
    Base.metadata.create_all(writer.get_bind())
    writer.add(
        CorrespondenceSection(
            arquivo="csec.csv",
            membro="a",
            geracao="2026-10-08",
            sg_uf="SE",
            cd_municipio="03105",
            nm_municipio="Aracaju",
        )
    )
    writer.commit()
    writer.close()
    names = AsyncPostgresMunicipalityNames(SyncSessionBridge(sessions()))
    assert asyncio.run(names.names("se")) == {3105: "Aracaju"}


def test_municipality_names_keep_domain_errors_and_wrap_driver_errors() -> None:
    broken = ScriptedSession()
    broken.push(("abc", "Aracaju"))
    names = AsyncPostgresMunicipalityNames(SyncSessionBridge(broken))
    with pytest.raises(ElectionError) as domain:
        asyncio.run(names.names("SE"))
    assert domain.value.__cause__ is None
    failed = ScriptedSession()
    failed.fail = psycopg.Error("down")
    names = AsyncPostgresMunicipalityNames(SyncSessionBridge(failed))
    with pytest.raises(ElectionError) as driver:
        asyncio.run(names.names("SE"))
    assert isinstance(driver.value.__cause__, psycopg.Error)
    assert str(driver.value) == "database read failed"


def test_power_store_round_trip_and_driver_errors() -> None:
    sessions = memory_sessions()
    ready = sessions()
    Base.metadata.create_all(ready.get_bind())
    ready.close()
    store = AsyncPostgresPowerReportStore(SyncSessionBridge(sessions()))
    assert asyncio.run(store.load(2026, 1, "presidente")) is None
    cell = StoredCell("municipio", "1120", "Aracaju", 20, 13, 5, 1)
    moment = asyncio.run(store.save(2026, 1, "presidente", (cell,)))
    loaded = asyncio.run(store.load(2026, 1, "presidente"))
    assert loaded == StoredReport((cell,), moment)
    failed = ScriptedSession()
    failed.fail = psycopg.Error("down")
    broken = AsyncPostgresPowerReportStore(SyncSessionBridge(failed))
    with pytest.raises(ElectionError) as caught:
        asyncio.run(broken.load(2026, 1, "presidente"))
    assert isinstance(caught.value.__cause__, psycopg.Error)


def test_power_store_loads_only_the_requested_levels() -> None:
    sessions = memory_sessions()
    ready = sessions()
    Base.metadata.create_all(ready.get_bind())
    ready.close()
    store = AsyncPostgresPowerReportStore(SyncSessionBridge(sessions()))
    city = StoredCell("municipio", "1120", "ARACAJU (SE)", 20, 13, 5, 1)
    state = StoredCell("uf", "SE", "Sergipe", 20, 13, 5, 1)
    moment = asyncio.run(store.save(2026, 2, "governador", (city, state)))
    loaded = asyncio.run(store.load_levels(2026, 2, "governador", ("uf",)))
    assert loaded == StoredReport((state,), moment)
    assert asyncio.run(store.load_levels(2026, 1, "governador", ("uf",))) is None


def test_power_store_keeps_a_domain_clock_error() -> None:
    session = ScriptedSession()
    session.push(SimpleNamespace(gerado_em=datetime(2026, 10, 8, 14, 30)))
    session.push()
    store = AsyncPostgresPowerReportStore(SyncSessionBridge(session))
    with pytest.raises(ElectionError) as caught:
        asyncio.run(store.load(2026, 1, "presidente"))
    assert caught.value.__cause__ is None
    assert "power report store failed" not in str(caught.value)


def test_cross_store_round_trip_with_and_without_governor() -> None:
    sessions = memory_sessions()
    ready = sessions()
    Base.metadata.create_all(ready.get_bind())
    ready.close()
    store = AsyncPostgresPresidentGovernorStore(SyncSessionBridge(sessions()))
    assert asyncio.run(store.load(2026, 1)) is None
    president = CargoTally((PartyTally(13, 5, 1),), 1, 0)
    governor = CargoTally((PartyTally(22, 4, 0),), 0, 1)
    place = MunicipalPlace("SE", "1120", "Aracaju", president, governor)
    moment = asyncio.run(store.save(2026, 1, (place,)))
    loaded = asyncio.run(store.load(2026, 1))
    assert loaded == StoredCrossReport((place,), moment)
    solo = MunicipalPlace("SE", "1120", "Aracaju", president, None)
    replaced = asyncio.run(store.save(2026, 1, (solo,)))
    assert asyncio.run(store.load(2026, 1)) == StoredCrossReport((solo,), replaced)
    failed = ScriptedSession()
    failed.fail = psycopg.Error("down")
    broken = AsyncPostgresPresidentGovernorStore(SyncSessionBridge(failed))
    with pytest.raises(ElectionError) as caught:
        asyncio.run(broken.load(2026, 1))
    assert isinstance(caught.value.__cause__, psycopg.Error)


def test_cross_store_keeps_a_domain_clock_error() -> None:
    session = ScriptedSession()
    session.push(SimpleNamespace(gerado_em=datetime(2026, 10, 8, 14, 30)))
    session.push()
    session.push()
    store = AsyncPostgresPresidentGovernorStore(SyncSessionBridge(session))
    with pytest.raises(ElectionError) as caught:
        asyncio.run(store.load(2026, 1))
    assert caught.value.__cause__ is None
    assert "cross report store failed" not in str(caught.value)
