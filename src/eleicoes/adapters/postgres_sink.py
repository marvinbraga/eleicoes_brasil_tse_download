"""Grava CSV no Postgres com COPY e mantém as visões de análise."""

import csv
import io
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from re import compile as compile_pattern
from typing import Protocol

from eleicoes.domain.errors import DatabaseConfigError, ElectionError, SchemaMismatchError
from eleicoes.domain.importing import ImportStatus, Provenance
from eleicoes.domain.tabular_contract import TabularContract

_TABLES = frozenset({"csec", "ccont"})
_COLUMN = compile_pattern(r"^[A-Z][A-Z0-9_]*$")
_DB_KEYS = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
)
_STATUS_LABEL = {
    ImportStatus.LOADED: "carregado",
    ImportStatus.IGNORED: "ignorado",
    ImportStatus.FAILED: "falhou",
}
_TABLES_SQL = (Path(__file__).resolve().parent / "sql" / "tables.sql").read_text(encoding="utf-8")
_VIEWS_SQL = (Path(__file__).resolve().parent / "sql" / "views.sql").read_text(encoding="utf-8")


class SqlCopy(Protocol):
    def write(self, data: bytes) -> None: ...

    def __enter__(self) -> "SqlCopy": ...

    def __exit__(self, *args: object) -> None: ...


class SqlCursor(Protocol):
    rowcount: int

    def execute(self, query: str, params: Sequence[object] | None = None) -> object: ...

    def copy(self, statement: str) -> SqlCopy: ...

    def __enter__(self) -> "SqlCursor": ...

    def __exit__(self, *args: object) -> None: ...


class SqlTransaction(Protocol):
    def __enter__(self) -> object: ...

    def __exit__(self, *args: object) -> None: ...


class SqlConnection(Protocol):
    def cursor(self) -> SqlCursor: ...

    def transaction(self) -> SqlTransaction: ...

    def close(self) -> None: ...


class PostgresTabularSink:
    def __init__(self, connect: "ConnectionFactory") -> None:
        self._connect = connect
        self._connection: SqlConnection | None = None

    def ensure_model(self) -> None:
        script = f"{_TABLES_SQL}\n{_VIEWS_SQL}"
        self._run(lambda cursor: _execute_script(cursor, script))

    def replace_member(
        self,
        contract: TabularContract,
        provenance: Provenance,
        csv_bytes: bytes,
    ) -> int:
        _check_header(contract, provenance.membro, csv_bytes)
        counts: list[int] = []

        def work(cursor: SqlCursor) -> None:
            counts.append(_replace(cursor, contract, provenance, csv_bytes))

        self._run(work)
        return counts[0]

    def record(
        self,
        provenance: Provenance,
        status: ImportStatus,
        linhas: int,
        tabela: str,
    ) -> None:
        self._run(lambda cursor: _audit(cursor, provenance, status, linhas, tabela))

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _run(self, work: "CursorWork") -> None:
        connection = self._open()
        with connection.transaction(), connection.cursor() as cursor:
            work(cursor)

    def _open(self) -> SqlConnection:
        if self._connection is None:
            self._connection = self._connect()
        return self._connection


class ConnectionFactory(Protocol):
    def __call__(self) -> SqlConnection: ...


class CursorWork(Protocol):
    def __call__(self, cursor: SqlCursor) -> None: ...


def connect_postgres(env: Mapping[str, str]) -> SqlConnection:
    missing = tuple(key for key in _DB_KEYS if _blank(env.get(key)))
    if missing:
        raise DatabaseConfigError(missing)
    try:
        port = int(env["POSTGRES_PORT"])
    except ValueError as exc:
        raise DatabaseConfigError(("POSTGRES_PORT",)) from exc
    import psycopg

    # cursor() is overloaded, so the connection is not a structural SqlConnection.
    return psycopg.connect(  # type: ignore[return-value]
        host=env["POSTGRES_HOST"],
        port=port,
        user=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
        dbname=env["POSTGRES_DB"],
    )


def _replace(
    cursor: SqlCursor,
    contract: TabularContract,
    provenance: Provenance,
    csv_bytes: bytes,
) -> int:
    _copy(cursor, contract, csv_bytes)
    _delete_rows(cursor, contract.table, provenance)
    inserted = _insert_rows(cursor, contract, provenance)
    _audit(cursor, provenance, ImportStatus.LOADED, inserted, contract.table)
    return inserted


def _copy(cursor: SqlCursor, contract: TabularContract, csv_bytes: bytes) -> None:
    table = _table(contract.table)
    columns = _columns(contract.columns)
    definitions = ", ".join(f"{column} text" for column in columns)
    column_list = ", ".join(columns)
    cursor.execute(f"CREATE TEMP TABLE staging_{table} ({definitions}) ON COMMIT DROP")
    statement = (
        f"COPY staging_{table} ({column_list}) FROM STDIN "
        "(FORMAT CSV, HEADER TRUE, DELIMITER ';', ENCODING 'LATIN1')"
    )
    with cursor.copy(statement) as stream:
        stream.write(csv_bytes)


def _delete_rows(cursor: SqlCursor, table: str, provenance: Provenance) -> None:
    cursor.execute(
        f"DELETE FROM raw.{_table(table)} WHERE arquivo = %s AND membro = %s",
        (provenance.arquivo, provenance.membro),
    )


def _insert_rows(cursor: SqlCursor, contract: TabularContract, provenance: Provenance) -> int:
    table = _table(contract.table)
    column_list = ", ".join(_columns(contract.columns))
    cursor.execute(
        f"INSERT INTO raw.{table} ({column_list}, arquivo, membro, geracao) "
        f"SELECT {column_list}, %s, %s, %s FROM staging_{table}",
        (provenance.arquivo, provenance.membro, provenance.geracao),
    )
    return cursor.rowcount


def _audit(
    cursor: SqlCursor,
    provenance: Provenance,
    status: ImportStatus,
    linhas: int,
    tabela: str,
) -> None:
    cursor.execute(
        "DELETE FROM raw.carga WHERE arquivo = %s AND membro = %s",
        (provenance.arquivo, provenance.membro),
    )
    cursor.execute(
        "INSERT INTO raw.carga "
        "(conjunto, turno, uf, arquivo, membro, tabela, geracao, linhas, situacao) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            provenance.conjunto,
            provenance.turno,
            provenance.uf,
            provenance.arquivo,
            provenance.membro,
            tabela,
            provenance.geracao,
            linhas,
            _STATUS_LABEL[status],
        ),
    )


def _execute_script(cursor: SqlCursor, script: str) -> None:
    for statement in _statements(script):
        cursor.execute(statement)


def _statements(script: str) -> Iterator[str]:
    for chunk in script.split(";"):
        statement = chunk.strip()
        if statement:
            yield statement


def _check_header(contract: TabularContract, member: str, csv_bytes: bytes) -> None:
    text = io.StringIO(csv_bytes.decode("latin-1"), newline="")
    try:
        header = tuple(next(csv.reader(text, delimiter=";")))
    except StopIteration as exc:
        raise SchemaMismatchError(member) from exc
    if header != contract.columns:
        raise SchemaMismatchError(member)


def _table(name: str) -> str:
    if name not in _TABLES:
        raise ElectionError(f"unknown table: {name}")
    return name


def _columns(names: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_column(name) for name in names)


def _column(name: str) -> str:
    if _COLUMN.fullmatch(name) is None:
        raise ElectionError(f"invalid column: {name}")
    return name.lower()


def _blank(value: str | None) -> bool:
    return value is None or value.strip() == ""
