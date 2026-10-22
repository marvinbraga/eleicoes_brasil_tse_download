"""Power-report cells through the ORM. No database socket."""

from datetime import UTC, datetime
from types import SimpleNamespace

import psycopg
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.dml import Delete, Insert
from sqlalchemy.sql.selectable import Select
from tests.adapters.orm_fakes import ScriptedSession, memory_sessions

import eleicoes.adapters.postgres_relatorio_poder as power_store
from eleicoes.adapters.orm.sessions import open_sync_session
from eleicoes.adapters.postgres_relatorio_poder import PostgresPowerReportStore, read_power_levels
from eleicoes.domain.errors import (
    DatabaseConfigError,
    ElectionError,
    InvalidNivelError,
    SchemaOutdatedError,
)
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.ports.relatorio_poder import StoredReport

_MOMENT = datetime(2026, 10, 8, 14, 30, tzinfo=UTC)
_LATER = datetime(2026, 10, 8, 15, 0, tzinfo=UTC)
_NAIVE = datetime(2026, 10, 8, 14, 30)
_ZERO = StoredCell("uf", "PA", "Para", 50, 13, 0, 0)
_VOTES = StoredCell("uf", "AC", "Acre", 80, 15, 4, 1)
_CITY = StoredCell("municipio", "1392", "RIO BRANCO", 100, 15, 10, 2)


@pytest.fixture(autouse=True)
def _schema_checks(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    seen: list[object] = []
    monkeypatch.setattr(power_store, "require_current_schema", seen.append)
    return seen


def test_postgres_ensure_model_checks_the_revision_once_without_ddl(
    _schema_checks: list[object],
) -> None:
    session = ScriptedSession()
    store = PostgresPowerReportStore(lambda: session)
    store.ensure_model()
    store.ensure_model()
    assert _schema_checks == [session]
    assert session.begins == 1
    assert session.executed == []


def test_injected_schema_check_replaces_the_default(_schema_checks: list[object]) -> None:
    session = ScriptedSession()
    seen: list[object] = []
    PostgresPowerReportStore(lambda: session, seen.append).ensure_model()
    assert seen == [session]
    assert _schema_checks == []


def test_outdated_schema_reaches_the_caller_as_is() -> None:
    def outdated(_session: object) -> None:
        raise SchemaOutdatedError((), "0002")

    store = PostgresPowerReportStore(ScriptedSession, outdated)
    with pytest.raises(SchemaOutdatedError):
        store.load(2026, 1, "presidente")


def test_load_reads_cells_after_ensuring_the_model() -> None:
    session = _session(
        (_clock(_MOMENT),),
        (_line(), _line(partido=13, votos_nominais=0, votos_legenda=0)),
    )
    store = _store(session)
    found = store.load(2026, 1, "deputadoFederal")
    assert found == StoredReport(
        (
            StoredCell("municipio", "1392", "RIO BRANCO", 100, 15, 10, 2),
            StoredCell("municipio", "1392", "RIO BRANCO", 100, 13, 0, 0),
        ),
        _MOMENT,
    )
    selects = [item for _begin, item in session.executed if isinstance(item, Select)]
    compiled = selects[-1].compile(dialect=postgresql.dialect())
    assert "relatorio_poder_linha" in str(compiled)
    assert "html" not in str(compiled)
    assert "deputadoFederal" not in str(compiled)
    assert "deputadoFederal" in compiled.params.values()


def test_load_returns_none_when_the_key_is_absent() -> None:
    store = _store(
        _session(
            (),
        )
    )
    assert store.load(2026, 1, "presidente") is None


def test_load_of_a_header_without_lines_is_an_empty_report() -> None:
    store = _store(_session((_clock(_MOMENT),), ()))
    assert store.load(2026, 1, "presidente") == StoredReport((), _MOMENT)


def test_save_upserts_cells_in_one_transaction_and_returns_the_clock() -> None:
    session = ScriptedSession()
    session.push(_MOMENT)
    store = _store(session)
    assert store.save(2026, 1, "governador", (_ZERO,)) == _MOMENT
    writes = [
        item
        for begin, item in session.executed
        if begin == session.begins and isinstance(item, (Insert, Delete))
    ]
    assert len([item for item in writes if isinstance(item, Insert)]) == 1
    assert len([item for item in writes if isinstance(item, Delete)]) == 1
    assert [entity.codigo for _begin, entity in session.added] == ["PA"]
    compiled = writes[0].compile(dialect=postgresql.dialect())
    script = str(compiled)
    assert "relatorio_poder" in script
    assert "html" not in script
    assert "governador" not in script
    assert "governador" in compiled.params.values()
    assert session.begins == 2


def test_save_and_load_round_trip_keeps_a_zero_vote_cell() -> None:
    sessions = memory_sessions()
    store = PostgresPowerReportStore(sessions)
    assert store.load(2026, 1, "deputadoFederal") is None
    cells = (_VOTES, _ZERO, _CITY)
    moment = store.save(2026, 1, "deputadoFederal", cells)
    assert moment.tzinfo is not None
    loaded = store.load(2026, 1, "deputadoFederal")
    assert loaded is not None
    assert loaded.gerado_em == moment
    assert set(loaded.cells) == set(cells)
    president_moment = store.save(2026, 1, "presidente", (_CITY,))
    assert store.load(2026, 1, "presidente") == StoredReport((_CITY,), president_moment)
    kept = store.load(2026, 1, "deputadoFederal")
    assert kept is not None
    assert kept.gerado_em == moment
    assert set(kept.cells) == set(cells)
    replaced = store.save(2026, 1, "deputadoFederal", (_ZERO,))
    assert store.load(2026, 1, "deputadoFederal") == StoredReport((_ZERO,), replaced)
    emptied = store.save(2026, 1, "deputadoFederal", ())
    assert store.load(2026, 1, "deputadoFederal") == StoredReport((), emptied)
    store.close()


def test_broken_rows_and_clocks_fail_as_election_errors() -> None:
    samples = (
        _session((_clock(_MOMENT),), (_line(nivel=1),)),
        _session((_clock(_MOMENT),), (_line(nome=None),)),
        _session((_clock(_MOMENT),), (_line(comparecimento="10"),)),
        _session((_clock(_MOMENT),), (_line(comparecimento=True),)),
        _session((_clock("yesterday"),), (_line(),)),
        _session((_clock(_NAIVE),), (_line(),)),
        _session((_clock(_MOMENT),), (_line(codigo="  "),)),
        _session((_clock(_MOMENT),), (_line(votos_nominais=-1),)),
        _session((_clock(_MOMENT), _clock(_LATER))),
        _session((_clock(_MOMENT),), (_line(nivel=None),)),
    )
    for session in samples:
        with pytest.raises(ElectionError):
            _store(session).load(2026, 1, "deputadoFederal")


def test_save_without_a_timestamp_fails() -> None:
    broken = (
        _session(()),
        _session(("text",)),
        _session(((),)),
        _session((_MOMENT, _MOMENT)),
    )
    for session in broken:
        with pytest.raises(ElectionError):
            _store(session).save(2026, 1, "deputadoFederal", ())


def test_driver_errors_become_election_errors() -> None:
    session = ScriptedSession()
    session.fail = psycopg.Error("down")
    with pytest.raises(ElectionError) as caught:
        _store(session).load(2026, 1, "deputadoFederal")
    assert isinstance(caught.value.__cause__, psycopg.Error)


def test_missing_database_settings_fail_before_a_socket() -> None:
    store = PostgresPowerReportStore(lambda: open_sync_session({}))
    with pytest.raises(DatabaseConfigError):
        store.save(2026, 1, "deputadoFederal", ())


def test_connection_is_reused_until_close_and_reopened_after() -> None:
    session = ScriptedSession()
    session.fixed = []
    opened = {"count": 0}

    def connect() -> ScriptedSession:
        opened["count"] += 1
        return session

    store = PostgresPowerReportStore(connect)
    store.close()
    assert store.load(2026, 1, "deputadoFederal") is None
    assert store.load(2024, 2, "presidente") is None
    store.close()
    store.close()
    assert store.load(2026, 1, "deputadoFederal") is None
    store.close()
    assert opened["count"] == 2
    assert session.closed == 2
    assert session.begins == 4


def _store(session: ScriptedSession) -> PostgresPowerReportStore:
    return PostgresPowerReportStore(lambda bound=session: bound)


def _session(*batches: tuple[object, ...]) -> ScriptedSession:
    session = ScriptedSession()
    for batch in batches:
        session.push(*batch)
    return session


def _clock(moment: object) -> SimpleNamespace:
    return SimpleNamespace(gerado_em=moment)


def _line(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "nivel": "municipio",
        "codigo": "1392",
        "nome": "RIO BRANCO",
        "comparecimento": 100,
        "partido": 15,
        "votos_nominais": 10,
        "votos_legenda": 2,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_read_power_levels_keeps_only_the_requested_levels() -> None:
    sessions = memory_sessions()
    store = PostgresPowerReportStore(sessions)
    moment = store.save(2026, 1, "deputadoFederal", (_VOTES, _ZERO, _CITY))
    session = sessions()
    with session.begin():
        cidades = read_power_levels(session, 2026, 1, "deputadoFederal", ("municipio",))
        estados = read_power_levels(session, 2026, 1, "deputadoFederal", ("uf", "pais"))
        ausente = read_power_levels(session, 2026, 1, "senador", ("uf",))
    assert cidades == StoredReport((_CITY,), moment)
    assert estados is not None
    assert set(estados.cells) == {_VOTES, _ZERO}
    assert ausente is None
    with pytest.raises(InvalidNivelError):
        read_power_levels(session, 2026, 1, "deputadoFederal", ("estado",))
    with pytest.raises(InvalidNivelError):
        read_power_levels(session, 2026, 1, "deputadoFederal", ())
    store.close()
