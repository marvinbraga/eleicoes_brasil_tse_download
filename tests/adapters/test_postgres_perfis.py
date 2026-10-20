"""Stored-line reader. The SQL stays in analise and does not touch the ballot raw tables."""

from collections.abc import Mapping

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.selectable import Select
from tests.adapters.orm_fakes import ScriptedSession

from eleicoes.adapters.postgres_perfis import PostgresStoredLines
from eleicoes.domain.classe_governador import ClassLine
from eleicoes.domain.errors import InconsistentCellError, StoredReadError
from eleicoes.domain.perfis import ProfileLine


def test_profile_query_is_one_select_with_a_null_ballot() -> None:
    session = ScriptedSession()
    session.push(("1392", "RIO BRANCO", 100, 13, 10, 2, None, None))
    reader = PostgresStoredLines(lambda: session)

    found = reader.profile_lines(2026, 1, "senador")

    assert found == (ProfileLine("1392", "RIO BRANCO", 100, 13, 10, 2, None, None),)
    selects = [item for _begin, item in session.executed if isinstance(item, Select)]
    assert len(selects) == 1
    compiled = selects[0].compile(dialect=postgresql.dialect())
    sql = str(compiled).lower()
    assert "analise.relatorio_poder_linha" in sql
    assert "analise.relatorio_presidente_governador_cedula" in sql
    assert "left outer join" in sql or "left join" in sql
    assert "boletim" not in sql
    assert "secoes" not in sql
    assert "raw." not in sql
    assert "senador" not in sql
    assert "senador" in compiled.params.values()
    assert "municipio" in compiled.params.values()
    reader.close()
    assert session.closed == 1


def test_class_query_reads_both_cargos_and_skips_the_cedula() -> None:
    session = ScriptedSession()
    session.push(("presidente", "1", "A", 80, 13, 10, 0))
    reader = PostgresStoredLines(lambda: session)

    found = reader.class_lines(2026, 1)

    assert found == (ClassLine("presidente", "1", "A", 80, 13, 10, 0),)
    selects = [item for _begin, item in session.executed if isinstance(item, Select)]
    compiled = selects[0].compile(dialect=postgresql.dialect())
    sql = str(compiled).lower()
    assert "cedula" not in sql
    assert "boletim" not in sql
    assert "secoes" not in sql
    assert _bound(compiled.params) >= {"presidente", "governador", "municipio"}
    reader.close()


def test_municipal_ufs_reads_president_lines_once_per_code() -> None:
    session = ScriptedSession()
    session.push(("1", "SP"), ("2", "MG"))
    reader = PostgresStoredLines(lambda: session)

    assert reader.municipal_ufs(2026, 1) == (("1", "SP"), ("2", "MG"))
    selects = [item for _begin, item in session.executed if isinstance(item, Select)]
    assert len(selects) == 1
    compiled = selects[0].compile(dialect=postgresql.dialect())
    sql = str(compiled).lower()
    table = "analise.relatorio_presidente_governador_linha"
    assert f"select distinct {table}.codigo, {table}.uf \nfrom {table}" in sql
    assert f"{table}.cargo = %(cargo_1)s" in sql
    assert f"order by {table}.uf, {table}.codigo" in sql
    assert "boletim" not in sql
    assert "raw." not in sql
    assert _bound(compiled.params) >= {2026, 1, "presidente"}
    reader.close()


def test_municipal_ufs_rejects_a_bad_row_and_translates_the_driver() -> None:
    session = ScriptedSession()
    session.push(("1", "SP", "extra"))
    with pytest.raises(InconsistentCellError):
        PostgresStoredLines(lambda: session).municipal_ufs(2026, 1)

    broken = ScriptedSession()
    broken.fail = SQLAlchemyError("nope")
    with pytest.raises(StoredReadError):
        PostgresStoredLines(lambda: broken).municipal_ufs(2026, 1)


def test_bad_row_stays_a_domain_error_and_the_driver_is_translated() -> None:
    session = ScriptedSession()
    session.push(("short",))
    reader = PostgresStoredLines(lambda: session)
    with pytest.raises(InconsistentCellError):
        reader.profile_lines(2026, 1, "presidente")

    broken = ScriptedSession()
    broken.fail = SQLAlchemyError("nope")
    with pytest.raises(StoredReadError, match="Não foi possível ler o relatório gravado."):
        PostgresStoredLines(lambda: broken).profile_lines(2026, 1, "presidente")


def test_close_without_a_session_is_a_no_op() -> None:
    session = ScriptedSession()
    PostgresStoredLines(lambda: session).close()
    assert session.closed == 0


def _bound(params: Mapping[str, object]) -> set[object]:
    found: set[object] = set()
    for value in params.values():
        if isinstance(value, (list, tuple)):
            found.update(value)
            continue
        found.add(value)
    return found


def test_non_sequence_and_bool_counts_are_rejected() -> None:
    session = ScriptedSession()
    session.push(5)
    with pytest.raises(InconsistentCellError):
        PostgresStoredLines(lambda: session).class_lines(2026, 1)

    flagged = ScriptedSession()
    flagged.push(("1", "A", 10, 13, 4, 1, True, None))
    with pytest.raises(InconsistentCellError):
        PostgresStoredLines(lambda: flagged).profile_lines(2026, 1, "presidente")
