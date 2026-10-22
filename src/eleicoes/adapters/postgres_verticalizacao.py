"""Reads the stored power lines of the five offices. One SELECT, analise schema only."""

from collections.abc import Callable, Sequence
from typing import Final, TypeVar

import psycopg
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable

from eleicoes.adapters.orm.models import PowerReportLine
from eleicoes.adapters.orm.sessions import SyncSessionFactory
from eleicoes.domain.errors import ElectionError, InconsistentCellError, StoredReadError
from eleicoes.domain.verticalizacao import CARGOS, VerticalLine

_LEVELS: Final = ("municipio", "uf")
_WIDTH: Final = 7
_T = TypeVar("_T")


class PostgresVerticalLines:
    def __init__(self, sessions: SyncSessionFactory) -> None:
        self._sessions = sessions
        self._session: Session | None = None

    def vertical_lines(self, ano: int, turno: int) -> tuple[VerticalLine, ...]:
        return self._guard(lambda: self._lines(ano, turno))

    def close(self) -> None:
        session = self._session
        self._session = None
        if session is not None:
            session.close()

    def _lines(self, ano: int, turno: int) -> tuple[VerticalLine, ...]:
        with self._open().begin():
            fetched = self._open().execute(vertical_statement(ano, turno)).all()
        return tuple(_line(_as_tuple(row)) for row in fetched)

    def _guard(self, work: Callable[[], _T]) -> _T:
        try:
            return work()
        except ElectionError:
            raise
        except (SQLAlchemyError, psycopg.Error) as exc:
            raise StoredReadError() from exc

    def _open(self) -> Session:
        if self._session is None:
            self._session = self._sessions()
        return self._session


def vertical_statement(ano: int, turno: int) -> Executable:
    votos = (PowerReportLine.votos_nominais + PowerReportLine.votos_legenda).label("votos")
    return select(
        PowerReportLine.cargo,
        PowerReportLine.nivel,
        PowerReportLine.codigo,
        PowerReportLine.nome,
        PowerReportLine.comparecimento,
        PowerReportLine.partido,
        votos,
    ).where(
        PowerReportLine.ano == ano,
        PowerReportLine.turno == turno,
        PowerReportLine.nivel.in_(_LEVELS),
        PowerReportLine.cargo.in_(CARGOS),
        (PowerReportLine.votos_nominais + PowerReportLine.votos_legenda) > 0,
    )


def _line(row: tuple[object, ...]) -> VerticalLine:
    if len(row) != _WIDTH:
        raise InconsistentCellError()
    return VerticalLine(
        _text(row[0]),
        _text(row[1]),
        _text(row[2]),
        _text(row[3]),
        _count(row[4]),
        _count(row[5]),
        _count(row[6]),
    )


def _as_tuple(row: object) -> tuple[object, ...]:
    if isinstance(row, tuple):
        return row
    if isinstance(row, Sequence) and not isinstance(row, (str, bytes)):
        return tuple(row)
    raise InconsistentCellError()


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise InconsistentCellError()
    return value


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InconsistentCellError()
    return value
