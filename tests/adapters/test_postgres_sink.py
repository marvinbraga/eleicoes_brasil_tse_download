import csv
import io
import sys
import types
from collections.abc import Sequence

import pytest

from eleicoes.adapters.orm.migrate import head_revision
from eleicoes.adapters.postgres_sink import PostgresTabularSink, connect_postgres
from eleicoes.domain.errors import DatabaseConfigError, SchemaMismatchError, SchemaOutdatedError
from eleicoes.domain.importing import ImportStatus, Provenance
from eleicoes.domain.tabular_contract import CSEC


def test_empty_csv_is_a_schema_mismatch() -> None:
    sink = PostgresTabularSink(_Connection)
    with pytest.raises(SchemaMismatchError):
        sink.replace_member(CSEC, _provenance(), b"")


def test_header_mismatch_does_not_open_a_connection() -> None:
    def connect() -> _Connection:
        raise AssertionError("connection opened")

    sink = PostgresTabularSink(connect)
    with pytest.raises(SchemaMismatchError):
        sink.replace_member(CSEC, _provenance(), b"A;B\r\n1;2\r\n")


def test_replace_copies_latin1_and_records_the_load() -> None:
    connection = _Connection()
    sink = PostgresTabularSink(lambda: connection)
    payload = _csv(CSEC.columns, ("04/10/2026",) * len(CSEC.columns))
    linhas = sink.replace_member(CSEC, _provenance(), payload)
    assert linhas == 2
    assert connection.cursor_obj.copies == [payload]
    statements = connection.cursor_obj.statements
    text = "\n".join(statement for statement, _params in statements)
    assert "CREATE TEMP TABLE staging_csec" in text
    assert "DELETE FROM raw.csec" in text
    assert "INSERT INTO raw.csec" in text
    assert any(bound[-1] == "carregado" for _statement, bound in statements if bound)
    sink.close()
    assert connection.closed is True


def test_ensure_model_checks_the_revision_then_applies_only_views() -> None:
    connection = _Connection()
    seen: list[object] = []
    sink = PostgresTabularSink(lambda: connection, seen.append)
    sink.ensure_model()
    text = "\n".join(statement for statement, _params in connection.cursor_obj.statements)
    assert seen == [connection.cursor_obj]
    assert "CREATE TABLE" not in text
    assert "CREATE OR REPLACE VIEW analise.secao" in text
    assert "CREATE OR REPLACE VIEW analise.resumo_uf" in text


def test_default_check_rejects_a_database_without_alembic_version() -> None:
    connection = _Connection()
    connection.cursor_obj.rows = [[(False,)]]
    sink = PostgresTabularSink(lambda: connection)
    with pytest.raises(SchemaOutdatedError) as caught:
        sink.ensure_model()
    assert caught.value.current == ()
    assert "VIEW" not in "\n".join(statement for statement, _ in connection.cursor_obj.statements)


def test_default_check_rejects_an_old_revision() -> None:
    connection = _Connection()
    connection.cursor_obj.rows = [[(True,)], [("0001",)]]
    with pytest.raises(SchemaOutdatedError) as caught:
        PostgresTabularSink(lambda: connection).ensure_model()
    assert caught.value.current == ("0001",)
    assert caught.value.expected == head_revision()


def test_default_check_accepts_the_head_revision() -> None:
    connection = _Connection()
    connection.cursor_obj.rows = [[(True,)], [(head_revision(),)]]
    PostgresTabularSink(lambda: connection).ensure_model()
    statements = [statement for statement, _ in connection.cursor_obj.statements]
    assert statements[1] == "SELECT version_num FROM alembic_version"
    assert any("CREATE OR REPLACE VIEW" in statement for statement in statements)


def test_record_writes_an_ignored_audit_row() -> None:
    connection = _Connection()
    sink = PostgresTabularSink(lambda: connection)
    sink.record(_provenance(), ImportStatus.IGNORED, 0, "")
    audits = [
        params for statement, params in connection.cursor_obj.statements if "VALUES" in statement
    ]
    assert audits[-1][-1] == "ignorado"


def test_missing_database_settings_fail_before_the_driver() -> None:
    with pytest.raises(DatabaseConfigError) as caught:
        connect_postgres({"POSTGRES_HOST": "postgres"})
    assert "POSTGRES_DB" in caught.value.missing


def test_connect_postgres_passes_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def connect(**kwargs: object) -> _Connection:
        captured.update(kwargs)
        return _Connection()

    module = types.ModuleType("psycopg")
    module.connect = connect  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psycopg", module)
    connect_postgres(
        {
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "eleicoes",
            "POSTGRES_PASSWORD": "eleicoes",
            "POSTGRES_DB": "eleicoes",
        }
    )
    assert captured["host"] == "postgres"
    assert captured["port"] == 5432
    assert captured["dbname"] == "eleicoes"


def test_invalid_port_is_configuration() -> None:
    with pytest.raises(DatabaseConfigError):
        connect_postgres(
            {
                "POSTGRES_HOST": "postgres",
                "POSTGRES_PORT": "abc",
                "POSTGRES_USER": "eleicoes",
                "POSTGRES_PASSWORD": "eleicoes",
                "POSTGRES_DB": "eleicoes",
            }
        )


class _Copy:
    def __init__(self, store: list[bytes]) -> None:
        self._store = store

    def write(self, data: bytes) -> None:
        self._store.append(data)

    def __enter__(self) -> "_Copy":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Cursor:
    def __init__(self) -> None:
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.copies: list[bytes] = []
        self.rows: list[list[tuple[object, ...]]] = []
        self.rowcount = 0

    def execute(self, query: str, params: Sequence[object] | None = None) -> None:
        bound = tuple(params or ())
        self.statements.append((query, bound))
        if query.startswith("INSERT INTO raw.csec") or query.startswith("INSERT INTO raw.ccont"):
            self.rowcount = 2

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows.pop(0)

    def copy(self, statement: str) -> _Copy:
        self.statements.append((statement, ()))
        return _Copy(self.copies)

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Connection:
    def __init__(self) -> None:
        self.cursor_obj = _Cursor()
        self.closed = False

    def cursor(self) -> _Cursor:
        return self.cursor_obj

    def transaction(self) -> "_Connection":
        return self

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _provenance() -> Provenance:
    return Provenance(
        "CESP_1t_AC_041020261259.zip", "csec.csv", "041020261259", "correspondencias", "1", "AC"
    )


def _csv(columns: tuple[str, ...], row: tuple[str, ...]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    writer.writerow(row)
    return buffer.getvalue().encode("latin-1")


def test_municipal_contract_loads_into_its_raw_table() -> None:
    from eleicoes.domain.municipal_contract import CONSULTA_VAGAS

    connection = _Connection()
    sink = PostgresTabularSink(lambda: connection)
    payload = _csv(CONSULTA_VAGAS.columns, ("x",) * len(CONSULTA_VAGAS.columns))
    sink.replace_member(CONSULTA_VAGAS, _provenance(), payload)
    text = "\n".join(statement for statement, _params in connection.cursor_obj.statements)
    assert "INSERT INTO raw.consulta_vagas" in text
