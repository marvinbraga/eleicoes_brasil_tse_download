"""Guarda as grades do relatório de poder. A senha fica na fábrica de sessão."""

from collections.abc import Callable
from datetime import datetime
from typing import TypeVar

import psycopg
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable, Select

from eleicoes.adapters.orm.models import Base, PowerReportHeader, PowerReportLine
from eleicoes.adapters.orm.schema import (
    apply_tables,
    dialect_name,
    is_postgresql,
    require_clock,
    server_clock,
)
from eleicoes.adapters.orm.sessions import SyncSessionFactory
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.ports.relatorio_poder import StoredReport

_MISSING = "power report was not stored"
_BROKEN = "power report row is incomplete"
_FAILED = "power report store failed"
_SQLITE = "sqlite"
_T = TypeVar("_T")


class PostgresPowerReportStore:
    def __init__(self, sessions: SyncSessionFactory) -> None:
        self._sessions = sessions
        self._session: Session | None = None

    def ensure_model(self) -> None:
        session = self._open()
        if not is_postgresql(session):
            Base.metadata.create_all(session.get_bind())
            return
        with session.begin():
            apply_tables(session)

    def load(self, ano: int, turno: int, cargo: str) -> StoredReport | None:
        return self._guard(lambda: self._load(ano, turno, cargo))

    def save(
        self,
        ano: int,
        turno: int,
        cargo: str,
        cells: tuple[StoredCell, ...],
    ) -> datetime:
        return self._guard(lambda: self._save(ano, turno, cargo, cells))

    def close(self) -> None:
        session = self._session
        self._session = None
        if session is not None:
            session.close()

    def _load(self, ano: int, turno: int, cargo: str) -> StoredReport | None:
        self.ensure_model()
        with self._open().begin():
            return read_power(self._open(), ano, turno, cargo)

    def _save(
        self,
        ano: int,
        turno: int,
        cargo: str,
        cells: tuple[StoredCell, ...],
    ) -> datetime:
        self.ensure_model()
        with self._open().begin():
            return write_power(self._open(), ano, turno, cargo, cells)

    def _guard(self, work: Callable[[], _T]) -> _T:
        try:
            return work()
        except ElectionError:
            raise
        except (SQLAlchemyError, psycopg.Error) as exc:
            raise ElectionError(_FAILED) from exc

    def _open(self) -> Session:
        if self._session is None:
            self._session = self._sessions()
        return self._session


def read_power(session: Session, ano: int, turno: int, cargo: str) -> StoredReport | None:
    headers = _headers(session, ano, turno, cargo)
    if headers is None:
        return None
    lines = session.execute(_lines(ano, turno, cargo)).scalars().all()
    moment = require_clock(session, headers.gerado_em, _BROKEN)
    return StoredReport(tuple(_cell(line) for line in lines), moment)


def write_power(
    session: Session,
    ano: int,
    turno: int,
    cargo: str,
    cells: tuple[StoredCell, ...],
) -> datetime:
    moment = _touch(session, ano, turno, cargo)
    removed = delete(PowerReportLine).where(
        PowerReportLine.ano == ano,
        PowerReportLine.turno == turno,
        PowerReportLine.cargo == cargo,
    )
    session.execute(removed)
    for cell in cells:
        session.add(_stored_line(ano, turno, cargo, cell))
    return moment


def _headers(session: Session, ano: int, turno: int, cargo: str) -> PowerReportHeader | None:
    found = tuple(session.execute(_header(ano, turno, cargo)).scalars().all())
    if not found:
        return None
    if len(found) != 1:
        raise ElectionError(_MISSING)
    return found[0]


def _header(ano: int, turno: int, cargo: str) -> Select[PowerReportHeader]:
    return select(PowerReportHeader).where(
        PowerReportHeader.ano == ano,
        PowerReportHeader.turno == turno,
        PowerReportHeader.cargo == cargo,
    )


def _lines(ano: int, turno: int, cargo: str) -> Select[PowerReportLine]:
    return select(PowerReportLine).where(
        PowerReportLine.ano == ano,
        PowerReportLine.turno == turno,
        PowerReportLine.cargo == cargo,
    )


def _touch(session: Session, ano: int, turno: int, cargo: str) -> datetime:
    clock = server_clock(session)
    index = ["ano", "turno", "cargo"]
    if dialect_name(session) == _SQLITE:
        saved = (
            sqlite_insert(PowerReportHeader)
            .values(ano=ano, turno=turno, cargo=cargo, gerado_em=clock)
            .on_conflict_do_update(index_elements=index, set_={"gerado_em": clock})
            .returning(PowerReportHeader.gerado_em)
        )
        return _clock(session, saved)
    saved_pg = (
        pg_insert(PowerReportHeader)
        .values(ano=ano, turno=turno, cargo=cargo, gerado_em=clock)
        .on_conflict_do_update(index_elements=index, set_={"gerado_em": clock})
        .returning(PowerReportHeader.gerado_em)
    )
    return _clock(session, saved_pg)


def _clock(session: Session, statement: Executable) -> datetime:
    found: object = session.execute(statement).scalar_one()
    return require_clock(session, found, _MISSING)


def _stored_line(ano: int, turno: int, cargo: str, cell: StoredCell) -> PowerReportLine:
    return PowerReportLine(
        ano=ano,
        turno=turno,
        cargo=cargo,
        nivel=cell.nivel,
        codigo=cell.codigo,
        nome=cell.nome,
        comparecimento=cell.comparecimento,
        partido=cell.partido,
        votos_nominais=cell.votos_nominais,
        votos_legenda=cell.votos_legenda,
    )


def _cell(line: PowerReportLine) -> StoredCell:
    return StoredCell(
        _text(line.nivel),
        _text(line.codigo),
        _text(line.nome),
        _count(line.comparecimento),
        _count(line.partido),
        _count(line.votos_nominais),
        _count(line.votos_legenda),
    )


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ElectionError(_BROKEN)
    return value


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ElectionError(_BROKEN)
    return value
