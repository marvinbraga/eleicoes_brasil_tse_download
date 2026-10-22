"""Apply the existing DDL script. Alembic is intentionally not introduced yet."""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from sqlalchemy import ColumnElement, func, inspect, literal, text
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.orm import Session

from eleicoes.domain.errors import ElectionError

_TABLES_SQL: Final = (Path(__file__).resolve().parent.parent / "sql" / "tables.sql").read_text(
    encoding="utf-8"
)
_POSTGRES: Final = "postgresql"
_SQLITE: Final = "sqlite"

# Columns an older DDL created as NOT NULL. The models no longer write them, so an
# existing database must accept NULL there. Columns and data are kept.
LEGACY_REQUIRED_COLUMNS: Final[tuple[tuple[str, str, str], ...]] = (
    ("analise", "relatorio_poder", "html"),
    ("analise", "relatorio_poder", "resumo"),
)

ColumnReader = Callable[[Session, str, str], Mapping[str, bool]]
"""(session, schema, table) -> column name -> nullable. Empty when the table is absent."""


def apply_tables(session: Session, read_columns: ColumnReader | None = None) -> None:
    for statement in _statements(_TABLES_SQL):
        session.execute(text(statement))
    _relax_legacy_columns(session, read_columns or reflect_columns)


def reflect_columns(session: Session, schema: str, table: str) -> Mapping[str, bool]:
    try:
        columns = inspect(session.connection()).get_columns(table, schema=schema)
    except NoSuchTableError:
        return {}
    return {str(column["name"]): bool(column["nullable"]) for column in columns}


def _relax_legacy_columns(session: Session, read_columns: ColumnReader) -> None:
    seen: dict[tuple[str, str], Mapping[str, bool]] = {}
    for schema, table, column in LEGACY_REQUIRED_COLUMNS:
        key = (schema, table)
        if key not in seen:
            seen[key] = read_columns(session, schema, table)
        if seen[key].get(column) is False:
            session.execute(
                text(f"ALTER TABLE {schema}.{table} ALTER COLUMN {column} DROP NOT NULL")
            )


def is_postgresql(session: Session) -> bool:
    return dialect_name(session) == _POSTGRES


def dialect_name(session: Session) -> str:
    return session.get_bind().dialect.name


def server_clock(session: Session) -> ColumnElement[datetime]:
    if dialect_name(session) == _POSTGRES:
        return func.now()
    return literal(datetime.now(UTC))


def require_clock(session: Session, value: object, message: str) -> datetime:
    if not isinstance(value, datetime):
        raise ElectionError(message)
    if value.tzinfo is not None:
        return value
    # SQLite has no timestamptz. Only the test dialect gets a UTC offset.
    if dialect_name(session) == _SQLITE:
        return value.replace(tzinfo=UTC)
    return value


def _statements(script: str) -> tuple[str, ...]:
    found: list[str] = []
    for chunk in script.split(";"):
        statement = chunk.strip()
        if statement:
            found.append(statement)
    return tuple(found)
