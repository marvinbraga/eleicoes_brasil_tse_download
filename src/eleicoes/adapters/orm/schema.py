"""Apply the existing DDL script. Alembic is intentionally not introduced yet."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from sqlalchemy import ColumnElement, func, literal, text
from sqlalchemy.orm import Session

from eleicoes.domain.errors import ElectionError

_TABLES_SQL: Final = (Path(__file__).resolve().parent.parent / "sql" / "tables.sql").read_text(
    encoding="utf-8"
)
_POSTGRES: Final = "postgresql"
_SQLITE: Final = "sqlite"


def apply_tables(session: Session) -> None:
    for statement in _statements(_TABLES_SQL):
        session.execute(text(statement))


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
