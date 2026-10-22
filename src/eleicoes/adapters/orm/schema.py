"""Dialect helpers for the ORM stores. Alembic owns the Postgres schema (see migrate.py)."""

from datetime import UTC, datetime
from typing import Final

from sqlalchemy import ColumnElement, func, literal
from sqlalchemy.orm import Session

from eleicoes.domain.errors import ElectionError

_POSTGRES: Final = "postgresql"
_SQLITE: Final = "sqlite"


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
