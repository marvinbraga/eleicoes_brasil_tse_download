"""Municipality names through the ORM. No database socket."""

import pytest
from sqlalchemy.dialects import postgresql
from tests.adapters.orm_fakes import ScriptedSession, memory_sessions

from eleicoes.adapters.orm.models import Base, CorrespondenceSection
from eleicoes.adapters.postgres_municipio import PostgresMunicipalityNames, name_query
from eleicoes.domain.errors import InvalidBoletimConsultaError


def test_name_query_binds_the_uf_code() -> None:
    compiled = name_query("AC").compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "cd_municipio" in sql
    assert "nm_municipio" in sql
    assert "csec" in sql
    assert "AC" not in sql
    assert "AC" in compiled.params.values()


def test_padded_codes_become_ints_and_blank_names_are_skipped() -> None:
    session = ScriptedSession()
    session.push(
        ("01007", " Xapuri "),
        ("01007", "Xapuri"),
        ("00100", " "),
        ("00100", ""),
        ("01392", "Rio Branco"),
        (1120, "Brasiléia"),
    )
    reader = PostgresMunicipalityNames(lambda: session)
    assert reader.names("ac") == {1007: "Xapuri", 1392: "Rio Branco", 1120: "Brasiléia"}


def test_sqlite_filters_by_the_uf_code() -> None:
    sessions = memory_sessions()
    writer = sessions()
    Base.metadata.create_all(writer.get_bind())
    writer.add(_section("a", "AC", "01007", " Xapuri "))
    writer.add(_section("b", "SE", "03105", "Aracaju"))
    writer.commit()
    writer.close()
    reader = PostgresMunicipalityNames(sessions)
    assert reader.names("ac") == {1007: "Xapuri"}
    reader.close()


def test_two_names_for_one_code_are_rejected() -> None:
    session = ScriptedSession()
    session.push(("01007", "Xapuri"), ("01007", "Outro"))
    reader = PostgresMunicipalityNames(lambda: session)
    with pytest.raises(InvalidBoletimConsultaError):
        reader.names("AC")


def test_bad_rows_are_rejected() -> None:
    samples = (
        (("01007",),),
        (("abc", "Xapuri"),),
        ((True, "Xapuri"),),
        (("01007", None),),
    )
    for rows in samples:
        session = ScriptedSession()
        session.push(*rows)
        reader = PostgresMunicipalityNames(lambda bound=session: bound)
        with pytest.raises(InvalidBoletimConsultaError):
            reader.names("AC")


def test_connection_is_reused_and_closed_once() -> None:
    session = ScriptedSession()
    session.fixed = []
    calls = {"opened": 0}

    def connect() -> ScriptedSession:
        calls["opened"] += 1
        return session

    reader = PostgresMunicipalityNames(connect)
    reader.close()
    assert reader.names("AC") == {}
    assert reader.names("AC") == {}
    reader.close()
    reader.close()
    assert calls["opened"] == 1
    assert session.closed == 1
    assert session.begins == 2


def _section(member: str, uf: str, code: str, name: str) -> CorrespondenceSection:
    return CorrespondenceSection(
        arquivo="csec.csv",
        membro=member,
        geracao="2026-10-08",
        sg_uf=uf,
        cd_municipio=code,
        nm_municipio=name,
    )
