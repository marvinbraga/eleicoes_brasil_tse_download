"""Seat votes through the ORM: SQLite for the round trip, a scripted session for Postgres."""

import asyncio
from datetime import UTC, datetime

import psycopg
import pytest
from sqlalchemy.orm import Session
from tests.adapters.orm_fakes import ScriptedSession, SyncSessionBridge, memory_sessions

import eleicoes.adapters.postgres_relatorio_cadeiras as seat_store
from eleicoes.adapters.postgres_relatorio_cadeiras import PostgresSeatVoteStore
from eleicoes.adapters.postgres_relatorio_cadeiras_async import AsyncPostgresSeatVoteStore
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.simulacao_cadeiras import VotoApurado

_FEDERAL = (
    VotoApurado("deputadoFederal", "AC", "nominal", 1301, 250),
    VotoApurado("deputadoFederal", "AC", "legenda", 13, 10),
)
_GOVERNOR = (VotoApurado("governador", "AC", "nominal", 13, 600),)


@pytest.fixture(autouse=True)
def _schema_checks(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    seen: list[object] = []
    monkeypatch.setattr(seat_store, "require_current_schema", seen.append)
    return seen


def test_save_load_and_header_round_trip() -> None:
    store = PostgresSeatVoteStore(memory_sessions())
    assert store.generated_at(2026, 1, "deputadoFederal") is None
    assert store.load(2026, 1) == ()
    first = store.save(2026, 1, "deputadoFederal", _FEDERAL)
    store.save(2026, 1, "governador", _GOVERNOR)
    assert first.tzinfo is not None
    assert store.generated_at(2026, 1, "deputadoFederal") == first
    loaded = store.load(2026, 1)
    assert [item.cargo for item in loaded] == ["deputadoFederal", "governador"]
    assert set(loaded[0].votos) == set(_FEDERAL)
    assert loaded[1].votos == _GOVERNOR
    store.close()


def test_save_replaces_the_previous_votes_of_the_cargo() -> None:
    store = PostgresSeatVoteStore(memory_sessions())
    store.save(2026, 1, "deputadoFederal", _FEDERAL)
    store.save(2026, 1, "deputadoFederal", _FEDERAL[:1])
    assert store.load(2026, 1)[0].votos == _FEDERAL[:1]


def test_empty_cargo_keeps_its_header() -> None:
    store = PostgresSeatVoteStore(memory_sessions())
    store.save(2026, 1, "deputadoDistrital", ())
    loaded = store.load(2026, 1)
    assert [(item.cargo, item.votos) for item in loaded] == [("deputadoDistrital", ())]


def test_vote_of_another_cargo_is_refused() -> None:
    store = PostgresSeatVoteStore(memory_sessions())
    with pytest.raises(ElectionError):
        store.save(2026, 1, "governador", _FEDERAL)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE analise.relatorio_cadeiras_voto SET numero = 'x'",
        "PRAGMA foreign_keys=OFF; INSERT INTO analise.relatorio_cadeiras_voto "
        "VALUES (2026, 1, 'senador', 'AC', 'nominal', 131, 5)",
    ],
)
def test_incomplete_stored_rows_are_refused(statement: str) -> None:
    sessions = memory_sessions()
    store = PostgresSeatVoteStore(sessions)
    store.save(2026, 1, "deputadoFederal", _FEDERAL)
    connection = sessions().connection().connection.dbapi_connection
    assert connection is not None
    connection.executescript(statement)
    with pytest.raises(ElectionError, match="seat vote row is incomplete"):
        store.load(2026, 1)


def test_postgres_checks_the_revision_once_without_ddl(_schema_checks: list[object]) -> None:
    session = ScriptedSession()
    store = PostgresSeatVoteStore(lambda: session)
    store.ensure_model()
    store.ensure_model()
    assert _schema_checks == [session]
    assert session.executed == []


def test_driver_errors_become_election_errors() -> None:
    def broken() -> Session:
        raise psycopg.OperationalError("down")

    with pytest.raises(ElectionError, match="seat vote store failed"):
        PostgresSeatVoteStore(broken).load(2026, 1)


def test_async_store_reads_what_the_sync_store_wrote() -> None:
    sessions = memory_sessions()
    PostgresSeatVoteStore(sessions).save(2026, 1, "governador", _GOVERNOR)
    bridge = SyncSessionBridge(sessions())
    loaded = asyncio.run(AsyncPostgresSeatVoteStore(bridge).load(2026, 1))  # type: ignore[arg-type]
    assert loaded[0].votos == _GOVERNOR
    assert loaded[0].gerado_em.tzinfo is not None
    assert loaded[0].gerado_em <= datetime.now(UTC)
