"""Session URL, dialect clocks, and mapped table names. No database socket."""

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.sql.elements import TextClause
from tests.adapters.orm_fakes import ScriptedSession, memory_sessions

from eleicoes.adapters.orm.models import (
    CorrespondenceSection,
    PowerReportHeader,
    PowerReportLine,
    PresidentGovernorBallot,
    PresidentGovernorHeader,
    PresidentGovernorLine,
)
from eleicoes.adapters.orm.schema import is_postgresql, require_clock, server_clock
from eleicoes.adapters.orm.sessions import AsyncSessionMaker, open_sync_session, sqlalchemy_url
from eleicoes.adapters.postgres_relatorio_poder import PostgresPowerReportStore
from eleicoes.domain.errors import ElectionError

_MOMENT = datetime(2026, 10, 8, 14, 30, tzinfo=UTC)
_NAIVE = datetime(2026, 10, 8, 14, 30)


def _env() -> dict[str, str]:
    return {
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": "1",
        "POSTGRES_USER": "eleicoes",
        "POSTGRES_PASSWORD": "eleicoes",
        "POSTGRES_DB": "eleicoes",
    }


def test_sync_and_async_sessions_use_psycopg_without_a_query() -> None:
    url = sqlalchemy_url(_env())
    assert url.drivername == "postgresql+psycopg"
    assert url.host == "127.0.0.1"
    assert url.database == "eleicoes"
    session = open_sync_session(_env())
    assert session.get_bind().dialect.name == "postgresql"
    session.close()

    async def close_maker() -> None:
        maker = AsyncSessionMaker(url)
        opened = maker()
        await opened.close()
        await maker.dispose()

    asyncio.run(close_maker())


def test_clocks_follow_the_dialect() -> None:
    postgres = ScriptedSession()
    sessions = memory_sessions()
    sqlite = sessions()
    assert is_postgresql(postgres) is True
    assert is_postgresql(sqlite) is False
    assert "now" in str(server_clock(postgres)).lower()
    assert str(server_clock(sqlite))
    assert require_clock(postgres, _MOMENT, "clock") == _MOMENT
    assert require_clock(postgres, _NAIVE, "clock") == _NAIVE
    assert require_clock(sqlite, _NAIVE, "clock") == _NAIVE.replace(tzinfo=UTC)
    assert require_clock(sqlite, _MOMENT, "clock") == _MOMENT
    with pytest.raises(ElectionError):
        require_clock(postgres, "yesterday", "clock")
    sqlite.close()


def test_sqlite_ensure_model_creates_the_mapped_schemas() -> None:
    sessions = memory_sessions()
    store = PostgresPowerReportStore(sessions)
    store.ensure_model()
    store.close()
    session = sessions()
    schemas = inspect(session.get_bind())
    analise = set(schemas.get_table_names(schema="analise"))
    raw = set(schemas.get_table_names(schema="raw"))
    session.close()
    assert {"relatorio_poder", "relatorio_poder_linha"} <= analise
    assert "csec" in raw


def test_mapped_tables_keep_the_existing_schemas() -> None:
    assert (PowerReportHeader.__table__.schema, PowerReportHeader.__tablename__) == (
        "analise",
        "relatorio_poder",
    )
    assert PowerReportLine.__tablename__ == "relatorio_poder_linha"
    assert PresidentGovernorHeader.__tablename__ == "relatorio_presidente_governador"
    assert PresidentGovernorLine.__tablename__ == "relatorio_presidente_governador_linha"
    assert PresidentGovernorBallot.__tablename__ == "relatorio_presidente_governador_cedula"
    assert (CorrespondenceSection.__table__.schema, CorrespondenceSection.__tablename__) == (
        "raw",
        "csec",
    )


def test_postgres_ensure_model_runs_the_ddl_script() -> None:
    session = ScriptedSession()
    PostgresPowerReportStore(lambda: session).ensure_model()
    text = "\n".join(item.text for _begin, item in session.executed if isinstance(item, TextClause))
    assert "CREATE SCHEMA IF NOT EXISTS analise" in text
    assert "CREATE TABLE IF NOT EXISTS raw.csec" in text
    assert "timestamptz" in text
