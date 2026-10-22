"""Legacy column relaxation after the DDL script. No Postgres socket."""

from collections.abc import Mapping

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import TextClause
from tests.adapters.orm_fakes import ScriptedSession, memory_sessions

from eleicoes.adapters.orm import schema
from eleicoes.adapters.orm.schema import LEGACY_REQUIRED_COLUMNS, apply_tables, reflect_columns
from eleicoes.adapters.postgres_relatorio_poder import PostgresPowerReportStore

_ALTER_HTML = "ALTER TABLE analise.relatorio_poder ALTER COLUMN html DROP NOT NULL"
_ALTER_RESUMO = "ALTER TABLE analise.relatorio_poder ALTER COLUMN resumo DROP NOT NULL"
_LEGACY_DDL = (
    "CREATE TABLE analise.relatorio_poder ("
    "ano integer NOT NULL, turno integer NOT NULL, cargo text NOT NULL, "
    "html text NOT NULL, resumo text NOT NULL, PRIMARY KEY (ano, turno, cargo))"
)


class _Columns:
    def __init__(self, found: Mapping[str, bool]) -> None:
        self._found = found
        self.asked: list[tuple[str, str]] = []

    def __call__(self, _session: Session, schema_name: str, table: str) -> Mapping[str, bool]:
        self.asked.append((schema_name, table))
        return self._found


def _alters(session: ScriptedSession) -> list[str]:
    return [
        item.text
        for _begin, item in session.executed
        if isinstance(item, TextClause) and item.text.startswith("ALTER TABLE")
    ]


def _apply(found: Mapping[str, bool]) -> tuple[ScriptedSession, _Columns]:
    session = ScriptedSession()
    columns = _Columns(found)
    apply_tables(session, columns)  # type: ignore[arg-type]
    return session, columns


def test_legacy_columns_are_a_final_list_of_report_text() -> None:
    assert LEGACY_REQUIRED_COLUMNS == (
        ("analise", "relatorio_poder", "html"),
        ("analise", "relatorio_poder", "resumo"),
    )


def test_required_legacy_columns_lose_not_null_after_the_ddl() -> None:
    session, columns = _apply({"ano": False, "html": False, "resumo": False})
    assert _alters(session) == [_ALTER_HTML, _ALTER_RESUMO]
    executed = [item.text for _begin, item in session.executed if isinstance(item, TextClause)]
    assert executed[-2:] == [_ALTER_HTML, _ALTER_RESUMO]
    assert set(columns.asked) == {("analise", "relatorio_poder")}


def test_optional_legacy_columns_are_left_alone() -> None:
    session, _columns = _apply({"ano": False, "html": True, "resumo": True})
    assert _alters(session) == []


def test_missing_legacy_columns_are_left_alone() -> None:
    session, _columns = _apply({"ano": False, "cargo": False})
    assert _alters(session) == []


def test_only_the_required_legacy_column_is_relaxed() -> None:
    session, _columns = _apply({"html": True, "resumo": False})
    assert _alters(session) == [_ALTER_RESUMO]


def test_relaxation_never_drops_columns_or_data() -> None:
    session, _columns = _apply({"html": False, "resumo": False})
    for statement in _alters(session):
        assert "DROP NOT NULL" in statement
        assert "DROP COLUMN" not in statement
        assert "DROP TABLE" not in statement


def test_store_ensure_model_relaxes_legacy_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(schema, "reflect_columns", _Columns({"html": False, "resumo": False}))
    session = ScriptedSession()
    PostgresPowerReportStore(lambda: session).ensure_model()
    assert _alters(session) == [_ALTER_HTML, _ALTER_RESUMO]


def test_store_ensure_model_on_a_new_database_has_no_alter() -> None:
    session = ScriptedSession()
    PostgresPowerReportStore(lambda: session).ensure_model()
    assert _alters(session) == []


def test_reflect_columns_reports_nullability_of_an_existing_table() -> None:
    sessions = memory_sessions()
    session = sessions()
    session.execute(text(_LEGACY_DDL.replace("resumo text NOT NULL", "resumo text")))
    found = reflect_columns(session, "analise", "relatorio_poder")
    assert found["html"] is False
    assert found["resumo"] is True
    assert found["ano"] is False


def test_reflect_columns_of_a_missing_table_is_empty() -> None:
    sessions = memory_sessions()
    assert reflect_columns(sessions(), "analise", "relatorio_poder") == {}


def test_sqlite_ensure_model_never_alters_legacy_columns() -> None:
    sessions = memory_sessions()
    setup = sessions()
    setup.execute(text(_LEGACY_DDL))
    setup.commit()
    PostgresPowerReportStore(sessions).ensure_model()
    found = reflect_columns(sessions(), "analise", "relatorio_poder")
    assert found["html"] is False
    assert found["resumo"] is False
