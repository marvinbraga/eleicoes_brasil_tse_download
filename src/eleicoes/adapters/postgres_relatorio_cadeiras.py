"""Stores the votes per candidate number behind the seat estimate. Seats are not stored."""

from collections.abc import Callable
from datetime import datetime
from typing import Final, TypeVar

import psycopg
from sqlalchemy import delete, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from eleicoes.adapters.orm.migrate import SchemaCheck, require_current_schema
from eleicoes.adapters.orm.models import Base, SeatReportHeader, SeatReportVote
from eleicoes.adapters.orm.schema import (
    dialect_name,
    is_postgresql,
    require_clock,
    server_clock,
)
from eleicoes.adapters.orm.sessions import SyncSessionFactory
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.simulacao_cadeiras import VotoApurado
from eleicoes.ports.relatorio_cadeiras import StoredSeatVotes

_MISSING: Final = "seat votes were not stored"
_BROKEN: Final = "seat vote row is incomplete"
_FAILED: Final = "seat vote store failed"
_SQLITE: Final = "sqlite"
_INDEX: Final = ["ano", "turno", "cargo"]
_T = TypeVar("_T")


class PostgresSeatVoteStore:
    def __init__(self, sessions: SyncSessionFactory, schema: SchemaCheck | None = None) -> None:
        self._sessions = sessions
        self._schema = schema if schema is not None else require_current_schema
        self._schema_checked = False
        self._session: Session | None = None

    def ensure_model(self) -> None:
        session = self._open()
        if not is_postgresql(session):
            Base.metadata.create_all(session.get_bind())
            return
        if self._schema_checked:
            return
        with session.begin():
            self._schema(session)
        self._schema_checked = True

    def load(self, ano: int, turno: int) -> tuple[StoredSeatVotes, ...]:
        def work() -> tuple[StoredSeatVotes, ...]:
            self.ensure_model()
            with self._open().begin():
                return read_seat_votes(self._open(), ano, turno)

        return self._guard(work)

    def generated_at(self, ano: int, turno: int, cargo: str) -> datetime | None:
        def work() -> datetime | None:
            self.ensure_model()
            with self._open().begin():
                return seat_header(self._open(), ano, turno, cargo)

        return self._guard(work)

    def save(self, ano: int, turno: int, cargo: str, votos: tuple[VotoApurado, ...]) -> datetime:
        def work() -> datetime:
            self.ensure_model()
            with self._open().begin():
                return write_seat_votes(self._open(), ano, turno, cargo, votos)

        return self._guard(work)

    def close(self) -> None:
        session = self._session
        self._session = None
        if session is not None:
            session.close()

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


def seat_header(session: Session, ano: int, turno: int, cargo: str) -> datetime | None:
    found = session.execute(
        select(SeatReportHeader.gerado_em).where(
            SeatReportHeader.ano == ano,
            SeatReportHeader.turno == turno,
            SeatReportHeader.cargo == cargo,
        )
    ).scalar_one_or_none()
    if found is None:
        return None
    return require_clock(session, found, _BROKEN)


def read_seat_votes(session: Session, ano: int, turno: int) -> tuple[StoredSeatVotes, ...]:
    headers = (
        session.execute(
            select(SeatReportHeader)
            .where(SeatReportHeader.ano == ano, SeatReportHeader.turno == turno)
            .order_by(SeatReportHeader.cargo)
        )
        .scalars()
        .all()
    )
    lines = session.execute(
        select(
            SeatReportVote.cargo,
            SeatReportVote.uf,
            SeatReportVote.tipo_voto,
            SeatReportVote.numero,
            SeatReportVote.votos,
        ).where(SeatReportVote.ano == ano, SeatReportVote.turno == turno)
    )
    by_cargo: dict[str, list[VotoApurado]] = {header.cargo: [] for header in headers}
    for cargo, uf, tipo, numero, votos in lines:
        found = by_cargo.get(cargo)
        if found is None:
            raise ElectionError(_BROKEN)
        found.append(_vote(cargo, uf, tipo, numero, votos))
    return tuple(
        StoredSeatVotes(
            header.cargo,
            tuple(by_cargo[header.cargo]),
            require_clock(session, header.gerado_em, _BROKEN),
        )
        for header in headers
    )


def write_seat_votes(
    session: Session,
    ano: int,
    turno: int,
    cargo: str,
    votos: tuple[VotoApurado, ...],
) -> datetime:
    if any(voto.cargo != cargo for voto in votos):
        raise ElectionError(_BROKEN)
    moment = _touch(session, ano, turno, cargo)
    session.execute(
        delete(SeatReportVote).where(
            SeatReportVote.ano == ano,
            SeatReportVote.turno == turno,
            SeatReportVote.cargo == cargo,
        )
    )
    if votos:
        session.execute(
            insert(SeatReportVote),
            [
                {
                    "ano": ano,
                    "turno": turno,
                    "cargo": cargo,
                    "uf": voto.uf,
                    "tipo_voto": voto.tipo_voto,
                    "numero": voto.numero,
                    "votos": voto.votos,
                }
                for voto in votos
            ],
        )
    return moment


def _touch(session: Session, ano: int, turno: int, cargo: str) -> datetime:
    clock = server_clock(session)
    values = {"ano": ano, "turno": turno, "cargo": cargo, "gerado_em": clock}
    if dialect_name(session) == _SQLITE:
        statement = (
            sqlite_insert(SeatReportHeader)
            .values(**values)
            .on_conflict_do_update(index_elements=_INDEX, set_={"gerado_em": clock})
            .returning(SeatReportHeader.gerado_em)
        )
    else:
        statement = (
            pg_insert(SeatReportHeader)
            .values(**values)
            .on_conflict_do_update(index_elements=_INDEX, set_={"gerado_em": clock})
            .returning(SeatReportHeader.gerado_em)
        )
    found: object = session.execute(statement).scalar_one()
    return require_clock(session, found, _MISSING)


def _vote(cargo: object, uf: object, tipo: object, numero: object, votos: object) -> VotoApurado:
    """Plain columns, not ORM entities: building 10^5 entities was most of the read time."""
    if not isinstance(cargo, str) or not isinstance(uf, str) or not isinstance(tipo, str):
        raise ElectionError(_BROKEN)
    if not isinstance(numero, int) or not isinstance(votos, int):
        raise ElectionError(_BROKEN)
    return VotoApurado(cargo, uf, tipo, numero, votos)
