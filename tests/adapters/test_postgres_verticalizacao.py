"""Vertical reader: one SELECT over the stored power lines, no ballot table."""

from collections.abc import Mapping

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.selectable import Select
from tests.adapters.orm_fakes import ScriptedSession

from eleicoes.adapters.postgres_verticalizacao import PostgresVerticalLines, vertical_statement
from eleicoes.domain.errors import InconsistentCellError, StoredReadError
from eleicoes.domain.verticalizacao import CARGOS, VerticalLine


def _bound(params: Mapping[str, object]) -> set[object]:
    found: set[object] = set()
    for value in params.values():
        if isinstance(value, (list, tuple)):
            found.update(value)
            continue
        found.add(value)
    return found


def test_one_select_reads_both_levels_and_the_five_cargos() -> None:
    session = ScriptedSession()
    session.push(("governador", "uf", "SP", "SP", 100, 13, 40))
    reader = PostgresVerticalLines(lambda: session)

    found = reader.vertical_lines(2026, 1)

    assert found == (VerticalLine("governador", "uf", "SP", "SP", 100, 13, 40),)
    selects = [item for _begin, item in session.executed if isinstance(item, Select)]
    assert len(selects) == 1
    compiled = selects[0].compile(dialect=postgresql.dialect())
    sql = str(compiled).lower()
    assert "analise.relatorio_poder_linha" in sql
    for forbidden in ("boletim", "secoes", "raw."):
        assert forbidden not in sql
    assert _bound(compiled.params) >= {"municipio", "uf", *CARGOS}
    select_part, where_part = sql.split("\nwhere ", 1)
    total = "votos_nominais + analise.relatorio_poder_linha.votos_legenda"
    assert total in select_part
    assert total in where_part
    reader.close()
    assert session.closed == 1


def test_statement_filters_year_and_turn() -> None:
    compiled = vertical_statement(2026, 2).compile(dialect=postgresql.dialect())
    assert {2026, 2} <= _bound(compiled.params)


def test_short_row_is_inconsistent() -> None:
    session = ScriptedSession()
    session.push(("governador", "uf", "SP", "SP", 100, 13))
    with pytest.raises(InconsistentCellError):
        PostgresVerticalLines(lambda: session).vertical_lines(2026, 1)


def test_non_sequence_row_is_inconsistent() -> None:
    session = ScriptedSession()
    session.push(7)
    with pytest.raises(InconsistentCellError):
        PostgresVerticalLines(lambda: session).vertical_lines(2026, 1)


def test_bad_cell_is_inconsistent() -> None:
    session = ScriptedSession()
    session.push(("governador", "uf", "SP", "SP", True, 13, 40))
    with pytest.raises(InconsistentCellError):
        PostgresVerticalLines(lambda: session).vertical_lines(2026, 1)


def test_driver_error_becomes_a_stored_read_error() -> None:
    broken = ScriptedSession()
    broken.fail = SQLAlchemyError("nope")
    with pytest.raises(StoredReadError):
        PostgresVerticalLines(lambda: broken).vertical_lines(2026, 1)


def test_close_is_idempotent() -> None:
    session = ScriptedSession()
    reader = PostgresVerticalLines(lambda: session)
    reader.close()
    assert session.closed == 0
    session.push()
    reader.vertical_lines(2026, 1)
    reader.close()
    reader.close()
    assert session.closed == 1
