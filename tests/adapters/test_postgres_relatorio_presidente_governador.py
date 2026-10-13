"""Cross-report cells against a fake cursor. No database socket."""

from collections.abc import Sequence
from datetime import UTC, datetime

import psycopg
import pytest

from eleicoes.adapters.postgres_relatorio_presidente_governador import (
    PostgresPresidentGovernorStore,
)
from eleicoes.composition.presidente_governador import build_cross_report_store
from eleicoes.domain.errors import DatabaseConfigError, ElectionError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport

_MOMENT = datetime(2026, 10, 8, 14, 30, tzinfo=UTC)
_LATER = datetime(2026, 10, 8, 15, 0, tzinfo=UTC)
_NAIVE = datetime(2026, 10, 8, 14, 30)
_HEADER = (
    "INSERT INTO analise.relatorio_presidente_governador (ano, turno) "
    "VALUES (%s, %s) "
    "ON CONFLICT (ano, turno) DO UPDATE "
    "SET gerado_em = now() "
    "RETURNING gerado_em"
)
_DELETE_LINHA = (
    "DELETE FROM analise.relatorio_presidente_governador_linha WHERE ano = %s AND turno = %s"
)
_DELETE_CEDULA = (
    "DELETE FROM analise.relatorio_presidente_governador_cedula WHERE ano = %s AND turno = %s"
)
_INSERT_LINHA = (
    "INSERT INTO analise.relatorio_presidente_governador_linha ("
    "ano, turno, uf, codigo, nome, cargo, partido, votos_nominais, votos_legenda) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
_INSERT_CEDULA = (
    "INSERT INTO analise.relatorio_presidente_governador_cedula ("
    "ano, turno, uf, codigo, cargo, branco, nulo) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
_LOAD_HEADER = (
    "SELECT gerado_em FROM analise.relatorio_presidente_governador "
    "WHERE ano = %s AND turno = %s"
)
_LOAD_LINHA = (
    "SELECT uf, codigo, nome, cargo, partido, votos_nominais, votos_legenda "
    "FROM analise.relatorio_presidente_governador_linha "
    "WHERE ano = %s AND turno = %s"
)
_LOAD_CEDULA = (
    "SELECT uf, codigo, cargo, branco, nulo "
    "FROM analise.relatorio_presidente_governador_cedula "
    "WHERE ano = %s AND turno = %s"
)


def test_ensure_model_creates_the_cross_tables_without_html_or_drop() -> None:
    connection = _Connection()
    PostgresPresidentGovernorStore(lambda: connection).ensure_model()
    text = "\n".join(statement for statement, _params in connection.statements)
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
    database = _Database(_MOMENT)
    store = PostgresPresidentGovernorStore(lambda: database)
    place = _place(branco=0, nulo=0, governor=False)
    moment = store.save(2026, 1, (place,))
    assert moment == _MOMENT
    loaded = store.load(2026, 1)
    assert loaded == StoredCrossReport((place,), _MOMENT)
    assert loaded is not None
    assert loaded.places[0].governador is None
    assert (loaded.places[0].presidente.branco, loaded.places[0].presidente.nulo) == (0, 0)
    writes = [item for item in database.traced if item[1].startswith(("INSERT", "DELETE"))]
    assert [item[1] for item in writes] == [
        _HEADER,
        _DELETE_LINHA,
        _DELETE_CEDULA,
        _INSERT_LINHA,
        _INSERT_CEDULA,
    ]
    assert len({item[0] for item in writes}) == 1
    cedula = next(item for item in writes if item[1] == _INSERT_CEDULA)
    assert cedula[2][-3:] == ("presidente", 0, 0)
    assert all(item[2][5] != "governador" for item in writes if item[1] == _INSERT_CEDULA)
    replacement = _place(nominal=40, legend=2, branco=3, nulo=4, governor=True)
    assert store.save(2026, 1, (replacement,)) == _MOMENT
    assert store.load(2026, 1) == StoredCrossReport((replacement,), _MOMENT)


def test_load_returns_none_when_the_key_is_absent() -> None:
    store = PostgresPresidentGovernorStore(lambda: _Database(_MOMENT))
    assert store.load(2026, 1) is None


def test_header_without_lines_is_an_empty_report() -> None:
    database = _Database(_MOMENT)
    store = PostgresPresidentGovernorStore(lambda: database)
    assert store.save(2026, 1, ()) == _MOMENT
    assert store.load(2026, 1) == StoredCrossReport((), _MOMENT)


def test_naive_clock_and_incomplete_rows_fail() -> None:
    naive = _Database(_NAIVE)
    naive.header[(2026, 1)] = _NAIVE
    with pytest.raises(ElectionError):
        PostgresPresidentGovernorStore(lambda: naive).load(2026, 1)
    broken = _Connection()
    broken.responses[_LOAD_HEADER] = [(_MOMENT,)]
    broken.responses[_LOAD_LINHA] = [("AC",)]
    broken.responses[_LOAD_CEDULA] = []
    with pytest.raises(ElectionError):
        PostgresPresidentGovernorStore(lambda: broken).load(2026, 1)


def test_driver_errors_become_election_errors() -> None:
    store = PostgresPresidentGovernorStore(lambda: _Connection(error=psycopg.Error("down")))
    with pytest.raises(ElectionError) as caught:
        store.load(2026, 1)
    assert isinstance(caught.value.__cause__, psycopg.Error)


def test_missing_database_settings_fail_before_a_socket() -> None:
    store = build_cross_report_store({})
    with pytest.raises(DatabaseConfigError):
        store.load(2026, 1)


def test_connection_is_reused_until_close() -> None:
    connection = _Database(_MOMENT)
    opened = {"count": 0}

    def connect() -> _Database:
        opened["count"] += 1
        return connection

    store = PostgresPresidentGovernorStore(connect)
    store.close()
    assert store.load(2026, 1) is None
    assert store.load(2024, 2) is None
    store.close()
    store.close()
    assert store.load(2026, 1) is None
    store.close()
    assert opened["count"] == 2
    assert connection.closed == 2


def test_save_statements_match_the_two_child_tables() -> None:
    connection = _Connection()
    connection.responses[_HEADER] = [(_LATER,)]
    store = PostgresPresidentGovernorStore(lambda: connection)
    assert store.save(2026, 1, (_place(governor=True),)) == _LATER
    queries = [
        query
        for query, _params in connection.statements
        if query.startswith(("INSERT", "DELETE", "SELECT"))
    ]
    assert _HEADER in queries
    assert _DELETE_LINHA in queries
    assert _DELETE_CEDULA in queries
    assert queries.count(_INSERT_LINHA) == 2
    assert queries.count(_INSERT_CEDULA) == 2
    assert _LOAD_HEADER not in queries


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


class _Cursor:
    def __init__(self, connection: "_Connection | _Database") -> None:
        self._connection = connection

    def execute(self, query: str, params: Sequence[object] | None = None) -> None:
        self._connection.execute(query, tuple(params or ()))

    def fetchall(self) -> list[tuple[object, ...]]:
        return list(self._connection.rows)

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _Connection:
    def __init__(self, *, error: BaseException | None = None) -> None:
        self.error = error
        self.responses: dict[str, list[tuple[object, ...]]] = {}
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.rows: list[tuple[object, ...]] = []
        self.transactions = 0
        self.closed = 0

    def execute(self, query: str, params: tuple[object, ...]) -> None:
        if self.error is not None:
            raise self.error
        self.statements.append((query, params))
        self.rows = list(self.responses.get(query, []))

    def cursor(self) -> _Cursor:
        return _Cursor(self)

    def transaction(self) -> "_Connection":
        self.transactions += 1
        return self

    def close(self) -> None:
        self.closed += 1

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _Database:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment
        self.header: dict[tuple[object, ...], datetime] = {}
        self.lines: dict[tuple[object, ...], list[tuple[object, ...]]] = {}
        self.cedulas: dict[tuple[object, ...], list[tuple[object, ...]]] = {}
        self.traced: list[tuple[int, str, tuple[object, ...]]] = []
        self.transactions = 0
        self.rows: list[tuple[object, ...]] = []
        self.closed = 0

    def execute(self, query: str, params: tuple[object, ...]) -> None:
        self.traced.append((self.transactions, query, params))
        self.rows = _apply(self, query, params)

    def cursor(self) -> _Cursor:
        return _Cursor(self)

    def transaction(self) -> "_Database":
        self.transactions += 1
        return self

    def close(self) -> None:
        self.closed += 1

    def __enter__(self) -> "_Database":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _apply(
    database: _Database,
    query: str,
    params: tuple[object, ...],
) -> list[tuple[object, ...]]:
    if query == _HEADER:
        database.header[params] = database.moment
        database.lines.setdefault(params, [])
        database.cedulas.setdefault(params, [])
        return [(database.moment,)]
    if query == _DELETE_LINHA:
        database.lines[params] = []
        return []
    if query == _DELETE_CEDULA:
        database.cedulas[params] = []
        return []
    if query == _INSERT_LINHA:
        database.lines.setdefault(params[:2], []).append(params[2:])
        return []
    if query == _INSERT_CEDULA:
        database.cedulas.setdefault(params[:2], []).append(params[2:])
        return []
    if query == _LOAD_HEADER:
        if params not in database.header:
            return []
        return [(database.header[params],)]
    if query == _LOAD_LINHA:
        return list(database.lines.get(params, []))
    if query == _LOAD_CEDULA:
        return list(database.cedulas.get(params, []))
    return []
