"""Power-report cells against a fake cursor. No database socket."""

from collections.abc import Sequence
from datetime import UTC, datetime

import psycopg
import pytest

from eleicoes.adapters.postgres_relatorio_poder import PostgresPowerReportStore
from eleicoes.adapters.postgres_sink import connect_postgres
from eleicoes.domain.errors import DatabaseConfigError, ElectionError
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.ports.relatorio_poder import StoredReport

_MOMENT = datetime(2026, 10, 8, 14, 30, tzinfo=UTC)
_LATER = datetime(2026, 10, 8, 15, 0, tzinfo=UTC)
_NAIVE = datetime(2026, 10, 8, 14, 30)
_HEADER = (
    "INSERT INTO analise.relatorio_poder (ano, turno, cargo) "
    "VALUES (%s, %s, %s) "
    "ON CONFLICT (ano, turno, cargo) DO UPDATE "
    "SET gerado_em = now() "
    "RETURNING gerado_em"
)
_DELETE = "DELETE FROM analise.relatorio_poder_linha WHERE ano = %s AND turno = %s AND cargo = %s"
_INSERT = (
    "INSERT INTO analise.relatorio_poder_linha ("
    "ano, turno, cargo, nivel, codigo, nome, comparecimento, "
    "partido, votos_nominais, votos_legenda) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
_LOAD = (
    "SELECT linha.nivel, linha.codigo, linha.nome, linha.comparecimento, "
    "linha.partido, linha.votos_nominais, linha.votos_legenda, "
    "cabecalho.gerado_em "
    "FROM analise.relatorio_poder AS cabecalho "
    "LEFT JOIN analise.relatorio_poder_linha AS linha "
    "ON linha.ano = cabecalho.ano AND linha.turno = cabecalho.turno "
    "AND linha.cargo = cabecalho.cargo "
    "WHERE cabecalho.ano = %s AND cabecalho.turno = %s AND cabecalho.cargo = %s"
)
_ZERO = StoredCell("uf", "PA", "Para", 50, 13, 0, 0)
_VOTES = StoredCell("uf", "AC", "Acre", 80, 15, 4, 1)
_CITY = StoredCell("municipio", "1392", "RIO BRANCO", 100, 15, 10, 2)


def test_ensure_model_creates_grade_tables_without_rendered_text() -> None:
    connection = _Connection([])
    PostgresPowerReportStore(lambda: connection).ensure_model()
    text = "\n".join(statement for statement, _params in connection.statements)
    report = text.split("CREATE TABLE IF NOT EXISTS analise.relatorio_poder", 1)[1]
    assert "CREATE SCHEMA IF NOT EXISTS analise" in text
    assert "CREATE TABLE IF NOT EXISTS analise.relatorio_poder_linha" in text
    assert "PRIMARY KEY (ano, turno, cargo)" in text
    assert "PRIMARY KEY (ano, turno, cargo, nivel, codigo, partido)" in text
    assert "FOREIGN KEY (ano, turno, cargo)" in text
    assert "REFERENCES analise.relatorio_poder (ano, turno, cargo)" in text
    assert "votos_nominais integer NOT NULL" in text
    assert "votos_legenda integer NOT NULL" in text
    assert "comparecimento integer NOT NULL" in text
    assert "html" not in text
    assert "resumo" not in text
    assert "fatia" not in text
    assert "DROP" not in text
    assert "uf " not in report


def test_load_reads_cells_after_ensuring_the_model() -> None:
    rows = [
        ("municipio", "1392", "RIO BRANCO", 100, 15, 10, 2, _MOMENT),
        ("municipio", "1392", "RIO BRANCO", 100, 13, 0, 0, _MOMENT),
    ]
    connection = _Connection(rows)
    store = PostgresPowerReportStore(lambda: connection)
    found = store.load(2026, 1, "deputadoFederal")
    assert found == StoredReport(
        (
            StoredCell("municipio", "1392", "RIO BRANCO", 100, 15, 10, 2),
            StoredCell("municipio", "1392", "RIO BRANCO", 100, 13, 0, 0),
        ),
        _MOMENT,
    )
    statement, params = connection.statements[-1]
    assert statement == _LOAD
    assert params == (2026, 1, "deputadoFederal")
    assert "html" not in statement
    assert "resumo" not in statement


def test_load_returns_none_when_the_key_is_absent() -> None:
    store = PostgresPowerReportStore(lambda: _Connection([]))
    assert store.load(2026, 1, "presidente") is None


def test_load_of_a_header_without_lines_is_an_empty_report() -> None:
    rows = [(None, None, None, None, None, None, None, _MOMENT)]
    store = PostgresPowerReportStore(lambda: _Connection(rows))
    assert store.load(2026, 1, "presidente") == StoredReport((), _MOMENT)


def test_save_upserts_cells_in_one_transaction_and_returns_the_clock() -> None:
    connection = _Connection([(_MOMENT,)])
    store = PostgresPowerReportStore(lambda: connection)
    moment = store.save(2026, 1, "governador", (_ZERO,))
    assert moment == _MOMENT
    writes = [
        (query, params)
        for query, params in connection.statements
        if query.startswith(("INSERT", "DELETE"))
    ]
    assert writes == [
        (_HEADER, (2026, 1, "governador")),
        (_DELETE, (2026, 1, "governador")),
        (_INSERT, (2026, 1, "governador", "uf", "PA", "Para", 50, 13, 0, 0)),
    ]
    write_ids = {item[0] for item in connection.traced if item[1].startswith(("INSERT", "DELETE"))}
    assert write_ids == {connection.transactions}
    script = "\n".join(query for query, _params in writes)
    assert "html" not in script
    assert "resumo" not in script
    assert "fatia" not in script


def test_save_and_load_round_trip_keeps_a_zero_vote_cell() -> None:
    database = _Database(_MOMENT)
    store = PostgresPowerReportStore(lambda: database)
    assert store.load(2026, 1, "deputadoFederal") is None
    cells = (_VOTES, _ZERO, _CITY)
    assert store.save(2026, 1, "deputadoFederal", cells) == _MOMENT
    assert store.load(2026, 1, "deputadoFederal") == StoredReport(cells, _MOMENT)
    assert store.save(2026, 1, "presidente", (_CITY,)) == _MOMENT
    assert store.load(2026, 1, "deputadoFederal") == StoredReport(cells, _MOMENT)
    assert store.save(2026, 1, "deputadoFederal", (_ZERO,)) == _MOMENT
    assert store.load(2026, 1, "deputadoFederal") == StoredReport((_ZERO,), _MOMENT)
    assert store.save(2026, 1, "deputadoFederal", ()) == _MOMENT
    assert store.load(2026, 1, "deputadoFederal") == StoredReport((), _MOMENT)
    writes = [item for item in database.traced if item[1].startswith(("INSERT", "DELETE"))]
    assert len({item[0] for item in writes[: 2 + len(cells)]}) == 1


def test_broken_rows_and_clocks_fail_as_election_errors() -> None:
    samples: tuple[list[tuple[object, ...]], ...] = (
        [("only",)],
        [("municipio", "1392", "RIO", 10, 13, 1, 0, _MOMENT), ("x",) * 8],
        [(1, "1392", "RIO", 10, 13, 1, 0, _MOMENT)],
        [("municipio", "1392", None, 10, 13, 1, 0, _MOMENT)],
        [("municipio", "1392", "RIO", "10", 13, 1, 0, _MOMENT)],
        [("municipio", "1392", "RIO", True, 13, 1, 0, _MOMENT)],
        [("municipio", "1392", "RIO", 10, 13, 1, 0, "yesterday")],
        [("municipio", "1392", "RIO", 10, 13, 1, 0, _NAIVE)],
        [("municipio", "  ", "RIO", 10, 13, 1, 0, _MOMENT)],
        [("municipio", "1392", "RIO", 10, 13, -1, 0, _MOMENT)],
        [
            ("municipio", "1392", "RIO", 10, 13, 1, 0, _MOMENT),
            ("municipio", "1392", "RIO", 10, 15, 1, 0, _LATER),
        ],
        [(None, "1392", "RIO", 10, 13, 1, 0, _MOMENT)],
    )
    for rows in samples:
        store = _store(rows)
        with pytest.raises(ElectionError):
            store.load(2026, 1, "deputadoFederal")


def test_save_without_a_timestamp_fails() -> None:
    broken: tuple[list[tuple[object, ...]], ...] = (
        [],
        [("text",)],
        [()],
        [(_MOMENT,), (_MOMENT,)],
    )
    for rows in broken:
        store = _store(rows)
        with pytest.raises(ElectionError):
            store.save(2026, 1, "deputadoFederal", ())


def test_driver_errors_become_election_errors() -> None:
    store = PostgresPowerReportStore(lambda: _Connection([], error=psycopg.Error("down")))
    with pytest.raises(ElectionError) as caught:
        store.load(2026, 1, "deputadoFederal")
    assert isinstance(caught.value.__cause__, psycopg.Error)


def test_missing_database_settings_fail_before_a_socket() -> None:
    store = PostgresPowerReportStore(lambda: connect_postgres({}))
    with pytest.raises(DatabaseConfigError):
        store.save(2026, 1, "deputadoFederal", ())


def test_connection_is_reused_until_close_and_reopened_after() -> None:
    connection = _Connection([(None, None, None, None, None, None, None, _MOMENT)])
    opened = {"count": 0}

    def connect() -> _Connection:
        opened["count"] += 1
        return connection

    store = PostgresPowerReportStore(connect)
    store.close()
    assert store.load(2026, 1, "deputadoFederal") is not None
    assert store.load(2024, 2, "presidente") is not None
    store.close()
    store.close()
    assert store.load(2026, 1, "deputadoFederal") is not None
    store.close()
    assert opened["count"] == 2
    assert connection.closed == 2


def _store(rows: list[tuple[object, ...]]) -> PostgresPowerReportStore:
    return PostgresPowerReportStore(lambda: _Connection(rows))


class _Cursor:
    def __init__(self, connection: "_Connection") -> None:
        self._connection = connection

    def execute(self, query: str, params: Sequence[object] | None = None) -> None:
        if self._connection.error is not None:
            raise self._connection.error
        bound = tuple(params or ())
        self._connection.statements.append((query, bound))
        self._connection.traced.append((self._connection.transactions, query, bound))

    def fetchall(self) -> list[tuple[object, ...]]:
        return list(self._connection.rows)

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _Connection:
    def __init__(
        self,
        rows: list[tuple[object, ...]],
        *,
        error: BaseException | None = None,
    ) -> None:
        self.rows = rows
        self.error = error
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.traced: list[tuple[int, str, tuple[object, ...]]] = []
        self.transactions = 0
        self.closed = 0

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
        self.headers: dict[tuple[object, ...], datetime] = {}
        self.lines: dict[tuple[object, ...], list[tuple[object, ...]]] = {}
        self.traced: list[tuple[int, str, tuple[object, ...]]] = []
        self.transactions = 0
        self.closed = 0

    def cursor(self) -> "_DbCursor":
        return _DbCursor(self)

    def transaction(self) -> "_Database":
        self.transactions += 1
        return self

    def close(self) -> None:
        self.closed += 1

    def __enter__(self) -> "_Database":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _DbCursor:
    def __init__(self, database: _Database) -> None:
        self._database = database
        self._rows: list[tuple[object, ...]] = []

    def execute(self, query: str, params: Sequence[object] | None = None) -> None:
        bound = tuple(params or ())
        self._database.traced.append((self._database.transactions, query, bound))
        self._rows = _apply(self._database, query, bound)

    def fetchall(self) -> list[tuple[object, ...]]:
        return list(self._rows)

    def __enter__(self) -> "_DbCursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _apply(
    database: _Database,
    query: str,
    params: tuple[object, ...],
) -> list[tuple[object, ...]]:
    if query.startswith("INSERT") and "relatorio_poder_linha" in query:
        return _insert_line(database, params)
    if query.startswith("DELETE"):
        database.lines[params] = []
        return []
    if query.startswith("INSERT"):
        return _insert_header(database, params)
    if query.startswith("SELECT"):
        return _select(database, params)
    return []


def _insert_header(
    database: _Database,
    params: tuple[object, ...],
) -> list[tuple[object, ...]]:
    key = params[:3]
    database.headers[key] = database.moment
    database.lines.setdefault(key, [])
    return [(database.moment,)]


def _insert_line(
    database: _Database,
    params: tuple[object, ...],
) -> list[tuple[object, ...]]:
    database.lines.setdefault(params[:3], []).append(params[3:])
    return []


def _select(database: _Database, params: tuple[object, ...]) -> list[tuple[object, ...]]:
    if params not in database.headers:
        return []
    moment = database.headers[params]
    lines = database.lines.get(params, [])
    if not lines:
        return [(None, None, None, None, None, None, None, moment)]
    return [(*line, moment) for line in lines]
