"""Cross-report places through the ORM. No database socket."""

from datetime import UTC, datetime
from types import SimpleNamespace

import psycopg
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.dml import Delete, Insert
from sqlalchemy.sql.elements import TextClause
from tests.adapters.orm_fakes import ScriptedSession, memory_sessions

from eleicoes.adapters.postgres_relatorio_presidente_governador import (
    PostgresPresidentGovernorStore,
    _places,
    read_cross,
)
from eleicoes.composition.presidente_governador import build_cross_report_store
from eleicoes.domain.errors import DatabaseConfigError, ElectionError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport

_MOMENT = datetime(2026, 10, 8, 14, 30, tzinfo=UTC)
_LATER = datetime(2026, 10, 8, 15, 0, tzinfo=UTC)
_NAIVE = datetime(2026, 10, 8, 14, 30)


def test_ensure_model_creates_the_cross_tables_without_html_or_drop() -> None:
    session = ScriptedSession()
    PostgresPresidentGovernorStore(lambda: session).ensure_model()
    text = "\n".join(item.text for _begin, item in session.executed if isinstance(item, TextClause))
    assert "CREATE TABLE IF NOT EXISTS analise.relatorio_presidente_governador (" in text
    assert "CREATE TABLE IF NOT EXISTS analise.relatorio_presidente_governador_linha" in text
    assert "CREATE TABLE IF NOT EXISTS analise.relatorio_presidente_governador_cedula" in text
    assert "PRIMARY KEY (ano, turno)" in text
    assert "PRIMARY KEY (ano, turno, uf, codigo, cargo, partido)" in text
    assert "PRIMARY KEY (ano, turno, uf, codigo, cargo)" in text
    assert "REFERENCES analise.relatorio_presidente_governador (ano, turno)" in text
    assert "branco integer NOT NULL" in text
    assert "nulo integer NOT NULL" in text
    assert "gerado_em timestamptz NOT NULL DEFAULT now()" in text
    assert "DROP" not in text
    assert "html" not in text
    assert "margem" not in text


def test_save_replaces_lines_and_cedulas_in_one_transaction() -> None:
    sessions = memory_sessions()
    store = PostgresPresidentGovernorStore(sessions)
    place = _place(branco=0, nulo=0, governor=False)
    moment = store.save(2026, 1, (place,))
    assert moment.tzinfo is not None
    loaded = store.load(2026, 1)
    assert loaded == StoredCrossReport((place,), moment)
    assert loaded is not None
    assert loaded.places[0].governador is None
    assert (loaded.places[0].presidente.branco, loaded.places[0].presidente.nulo) == (0, 0)
    replacement = _place(nominal=40, legend=2, branco=3, nulo=4, governor=True)
    replaced = store.save(2026, 1, (replacement,))
    assert store.load(2026, 1) == StoredCrossReport((replacement,), replaced)
    store.close()


def test_save_writes_both_child_tables_in_one_transaction() -> None:
    session = ScriptedSession()
    session.push(_LATER)
    store = PostgresPresidentGovernorStore(lambda: session)
    assert store.save(2026, 1, (_place(governor=True),)) == _LATER
    writes = [item for begin, item in session.executed if begin == session.begins]
    inserts = [item for item in writes if isinstance(item, Insert)]
    deletes = [item for item in writes if isinstance(item, Delete)]
    assert len(inserts) == 1
    assert len(deletes) == 2
    assert session.begins == 2
    compiled = "\n".join(str(item.compile(dialect=postgresql.dialect())) for item in deletes)
    assert "relatorio_presidente_governador_linha" in compiled
    assert "relatorio_presidente_governador_cedula" in compiled
    cargos = [entity.cargo for begin, entity in session.added if begin == session.begins]
    assert cargos.count("presidente") == 2
    assert cargos.count("governador") == 2


def test_load_returns_none_when_the_key_is_absent() -> None:
    store = PostgresPresidentGovernorStore(memory_sessions())
    assert store.load(2026, 1) is None
    store.close()


def test_header_without_lines_is_an_empty_report() -> None:
    store = PostgresPresidentGovernorStore(memory_sessions())
    moment = store.save(2026, 1, ())
    assert store.load(2026, 1) == StoredCrossReport((), moment)
    store.close()


def test_naive_clock_and_incomplete_rows_fail() -> None:
    session = _batches((_clock(_NAIVE),), (), ())
    with pytest.raises(ElectionError):
        PostgresPresidentGovernorStore(lambda: session).load(2026, 1)
    samples = (
        _batches(
            (_clock(_MOMENT), _clock(_LATER)),
        ),
        _batches((_clock(_MOMENT),), (_line(cargo="senador"),), ()),
        _batches((_clock(_MOMENT),), (_line(),), (_ballot(cargo="senador"),)),
        _batches((_clock(_MOMENT),), (_line(nome="A"), _line(nome="B")), ()),
        _batches((_clock(_MOMENT),), (), (_ballot(),)),
        _batches((_clock(_MOMENT),), (_line(),), ()),
        _batches(
            (_clock(_MOMENT),),
            (_line(), _line(cargo="governador", partido=22)),
            (_ballot(),),
        ),
        _batches((_clock(_MOMENT),), (_line(),), (_ballot(), _ballot(cargo="governador"))),
        _batches((_clock(_MOMENT),), (_line(votos_nominais=0, votos_legenda=0),), (_ballot(),)),
        _batches((_clock(_MOMENT),), (_line(partido=True),), (_ballot(),)),
        _batches((_clock(_MOMENT),), (_line(uf=1),), (_ballot(),)),
        _batches((_clock("yesterday"),), (), ()),
    )
    for rows in samples:
        with pytest.raises(ElectionError):
            read_cross(rows, 2026, 1)
    with pytest.raises(ElectionError):
        _places((("AC",),), ())
    with pytest.raises(ElectionError):
        _places((), (("AC", "10", "presidente"),))


def test_driver_errors_become_election_errors() -> None:
    session = ScriptedSession()
    session.fail = psycopg.Error("down")
    store = PostgresPresidentGovernorStore(lambda: session)
    with pytest.raises(ElectionError) as caught:
        store.load(2026, 1)
    assert isinstance(caught.value.__cause__, psycopg.Error)


def test_missing_database_settings_fail_before_a_socket() -> None:
    store = build_cross_report_store({})
    with pytest.raises(DatabaseConfigError):
        store.load(2026, 1)


def test_connection_is_reused_until_close() -> None:
    session = ScriptedSession()
    session.fixed = []
    opened = {"count": 0}

    def connect() -> ScriptedSession:
        opened["count"] += 1
        return session

    store = PostgresPresidentGovernorStore(connect)
    store.close()
    assert store.load(2026, 1) is None
    assert store.load(2024, 2) is None
    store.close()
    store.close()
    assert store.load(2026, 1) is None
    store.close()
    assert opened["count"] == 2
    assert session.closed == 2


def _place(
    *,
    nominal: int = 10,
    legend: int = 0,
    branco: int = 1,
    nulo: int = 2,
    governor: bool = True,
) -> MunicipalPlace:
    president = CargoTally((PartyTally(13, nominal, legend),), branco, nulo)
    governor_tally = None if not governor else CargoTally((PartyTally(22, 4, 1),), 0, 0)
    return MunicipalPlace("AC", "10", "Rio Branco (AC)", president, governor_tally)


def _batches(*groups: tuple[object, ...]) -> ScriptedSession:
    session = ScriptedSession()
    for group in groups:
        session.push(*group)
    return session


def _clock(moment: object) -> SimpleNamespace:
    return SimpleNamespace(gerado_em=moment)


def _line(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "uf": "AC",
        "codigo": "10",
        "nome": "Rio Branco",
        "cargo": "presidente",
        "partido": 13,
        "votos_nominais": 4,
        "votos_legenda": 1,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _ballot(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "uf": "AC",
        "codigo": "10",
        "cargo": "presidente",
        "branco": 1,
        "nulo": 0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)
