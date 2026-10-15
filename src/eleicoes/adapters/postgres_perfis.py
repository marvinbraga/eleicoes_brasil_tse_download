"""Reads stored municipal lines. One SELECT, analise schema only."""

from collections.abc import Callable, Sequence
from typing import TypeVar

import psycopg
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable

from eleicoes.adapters.orm.models import PowerReportLine, PresidentGovernorBallot
from eleicoes.adapters.orm.sessions import SyncSessionFactory
from eleicoes.domain.classe_governador import ClassLine
from eleicoes.domain.errors import ElectionError, InconsistentCellError, StoredReadError
from eleicoes.domain.perfis import ProfileLine

_MUNICIPIO = "municipio"
_PROFILE_WIDTH = 8
_CLASS_WIDTH = 7
_CLASS_CARGOS = ("presidente", "governador")
_T = TypeVar("_T")


class PostgresStoredLines:
    def __init__(self, sessions: SyncSessionFactory) -> None:
        self._sessions = sessions
        self._session: Session | None = None

    def profile_lines(self, ano: int, turno: int, cargo: str) -> tuple[ProfileLine, ...]:
        return self._guard(lambda: self._profile(ano, turno, cargo))

    def class_lines(self, ano: int, turno: int) -> tuple[ClassLine, ...]:
        return self._guard(lambda: self._classes(ano, turno))

    def close(self) -> None:
        session = self._session
        self._session = None
        if session is not None:
            session.close()

    def _profile(self, ano: int, turno: int, cargo: str) -> tuple[ProfileLine, ...]:
        with self._open().begin():
            fetched = self._open().execute(profile_statement(ano, turno, cargo)).all()
        return tuple(_profile_line(_as_tuple(row)) for row in fetched)

    def _classes(self, ano: int, turno: int) -> tuple[ClassLine, ...]:
        with self._open().begin():
            fetched = self._open().execute(class_statement(ano, turno)).all()
        return tuple(_class_line(_as_tuple(row)) for row in fetched)

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


def profile_statement(ano: int, turno: int, cargo: str) -> Executable:
    return (
        select(
            PowerReportLine.codigo,
            PowerReportLine.nome,
            PowerReportLine.comparecimento,
            PowerReportLine.partido,
            PowerReportLine.votos_nominais,
            PowerReportLine.votos_legenda,
            PresidentGovernorBallot.branco,
            PresidentGovernorBallot.nulo,
        )
        .outerjoin(
            PresidentGovernorBallot,
            and_(
                PresidentGovernorBallot.ano == PowerReportLine.ano,
                PresidentGovernorBallot.turno == PowerReportLine.turno,
                PresidentGovernorBallot.cargo == PowerReportLine.cargo,
                PresidentGovernorBallot.codigo == PowerReportLine.codigo,
            ),
        )
        .where(
            PowerReportLine.ano == ano,
            PowerReportLine.turno == turno,
            PowerReportLine.cargo == cargo,
            PowerReportLine.nivel == _MUNICIPIO,
        )
    )


def class_statement(ano: int, turno: int) -> Executable:
    return select(
        PowerReportLine.cargo,
        PowerReportLine.codigo,
        PowerReportLine.nome,
        PowerReportLine.comparecimento,
        PowerReportLine.partido,
        PowerReportLine.votos_nominais,
        PowerReportLine.votos_legenda,
    ).where(
        PowerReportLine.ano == ano,
        PowerReportLine.turno == turno,
        PowerReportLine.nivel == _MUNICIPIO,
        PowerReportLine.cargo.in_(_CLASS_CARGOS),
    )


def _profile_line(row: tuple[object, ...]) -> ProfileLine:
    if len(row) != _PROFILE_WIDTH:
        raise InconsistentCellError()
    return ProfileLine(
        _text(row[0]),
        _text(row[1]),
        _count(row[2]),
        _count(row[3]),
        _count(row[4]),
        _count(row[5]),
        _optional(row[6]),
        _optional(row[7]),
    )


def _class_line(row: tuple[object, ...]) -> ClassLine:
    if len(row) != _CLASS_WIDTH:
        raise InconsistentCellError()
    return ClassLine(
        _text(row[0]),
        _text(row[1]),
        _text(row[2]),
        _count(row[3]),
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
    if not isinstance(value, str) or value.strip() == "":
        raise InconsistentCellError()
    return value.strip()


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InconsistentCellError()
    return value


def _optional(value: object) -> int | None:
    if value is None:
        return None
    return _count(value)
