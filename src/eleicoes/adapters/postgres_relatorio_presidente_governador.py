"""Guarda os votos municipais do cruzamento. A senha fica na fábrica de sessão."""

from collections.abc import Callable
from datetime import datetime
from typing import Final, TypeVar

import psycopg
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable, Select

from eleicoes.adapters.orm.migrate import SchemaCheck, require_current_schema
from eleicoes.adapters.orm.models import (
    Base,
    PresidentGovernorBallot,
    PresidentGovernorHeader,
    PresidentGovernorLine,
)
from eleicoes.adapters.orm.schema import (
    dialect_name,
    is_postgresql,
    require_clock,
    server_clock,
)
from eleicoes.adapters.orm.sessions import SyncSessionFactory
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport

_LINE_WIDTH: Final = 7
_CEDULA_WIDTH: Final = 5
_PRESIDENT: Final = "presidente"
_GOVERNOR: Final = "governador"
_MISSING = "cross report was not stored"
_BROKEN = "cross report row is incomplete"
_FAILED = "cross report store failed"
_SQLITE = "sqlite"
_T = TypeVar("_T")


class PostgresPresidentGovernorStore:
    def __init__(
        self,
        sessions: SyncSessionFactory,
        schema: SchemaCheck | None = None,
    ) -> None:
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

    def load(self, ano: int, turno: int) -> StoredCrossReport | None:
        return self._guard(lambda: self._load(ano, turno))

    def save(
        self,
        ano: int,
        turno: int,
        places: tuple[MunicipalPlace, ...],
    ) -> datetime:
        return self._guard(lambda: self._save(ano, turno, places))

    def close(self) -> None:
        session = self._session
        self._session = None
        if session is not None:
            session.close()

    def _load(self, ano: int, turno: int) -> StoredCrossReport | None:
        self.ensure_model()
        with self._open().begin():
            return read_cross(self._open(), ano, turno)

    def _save(self, ano: int, turno: int, places: tuple[MunicipalPlace, ...]) -> datetime:
        self.ensure_model()
        with self._open().begin():
            return write_cross(self._open(), ano, turno, places)

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


def read_cross(session: Session, ano: int, turno: int) -> StoredCrossReport | None:
    header = _header(session, ano, turno)
    if header is None:
        return None
    lines = tuple(session.execute(_line_query(ano, turno)).scalars().all())
    ballots = tuple(session.execute(_ballot_query(ano, turno)).scalars().all())
    places = _places(_line_rows(lines), _ballot_rows(ballots))
    return StoredCrossReport(places, require_clock(session, header.gerado_em, _BROKEN))


def write_cross(
    session: Session,
    ano: int,
    turno: int,
    places: tuple[MunicipalPlace, ...],
) -> datetime:
    moment = _touch(session, ano, turno)
    session.execute(
        delete(PresidentGovernorLine).where(
            PresidentGovernorLine.ano == ano,
            PresidentGovernorLine.turno == turno,
        )
    )
    session.execute(
        delete(PresidentGovernorBallot).where(
            PresidentGovernorBallot.ano == ano,
            PresidentGovernorBallot.turno == turno,
        )
    )
    for place in places:
        _insert_place(session, ano, turno, place)
    return moment


def _header(session: Session, ano: int, turno: int) -> PresidentGovernorHeader | None:
    found = tuple(session.execute(_header_query(ano, turno)).scalars().all())
    if not found:
        return None
    if len(found) != 1:
        raise ElectionError(_MISSING)
    return found[0]


def _header_query(ano: int, turno: int) -> Select[PresidentGovernorHeader]:
    return select(PresidentGovernorHeader).where(
        PresidentGovernorHeader.ano == ano,
        PresidentGovernorHeader.turno == turno,
    )


def _line_query(ano: int, turno: int) -> Select[PresidentGovernorLine]:
    return select(PresidentGovernorLine).where(
        PresidentGovernorLine.ano == ano,
        PresidentGovernorLine.turno == turno,
    )


def _ballot_query(ano: int, turno: int) -> Select[PresidentGovernorBallot]:
    return select(PresidentGovernorBallot).where(
        PresidentGovernorBallot.ano == ano,
        PresidentGovernorBallot.turno == turno,
    )


def _touch(session: Session, ano: int, turno: int) -> datetime:
    clock = server_clock(session)
    index = ["ano", "turno"]
    if dialect_name(session) == _SQLITE:
        saved = (
            sqlite_insert(PresidentGovernorHeader)
            .values(ano=ano, turno=turno, gerado_em=clock)
            .on_conflict_do_update(index_elements=index, set_={"gerado_em": clock})
            .returning(PresidentGovernorHeader.gerado_em)
        )
        return _clock(session, saved)
    saved_pg = (
        pg_insert(PresidentGovernorHeader)
        .values(ano=ano, turno=turno, gerado_em=clock)
        .on_conflict_do_update(index_elements=index, set_={"gerado_em": clock})
        .returning(PresidentGovernorHeader.gerado_em)
    )
    return _clock(session, saved_pg)


def _clock(session: Session, statement: Executable) -> datetime:
    found: object = session.execute(statement).scalar_one()
    return require_clock(session, found, _MISSING)


def _insert_place(session: Session, ano: int, turno: int, place: MunicipalPlace) -> None:
    _insert_cargo(session, ano, turno, place, _PRESIDENT, place.presidente)
    if place.governador is not None:
        _insert_cargo(session, ano, turno, place, _GOVERNOR, place.governador)


def _insert_cargo(
    session: Session,
    ano: int,
    turno: int,
    place: MunicipalPlace,
    cargo: str,
    tally: CargoTally,
) -> None:
    for party in tally.parties:
        session.add(_line(ano, turno, place, cargo, party))
    session.add(_ballot(ano, turno, place, cargo, tally))


def _line(
    ano: int,
    turno: int,
    place: MunicipalPlace,
    cargo: str,
    party: PartyTally,
) -> PresidentGovernorLine:
    return PresidentGovernorLine(
        ano=ano,
        turno=turno,
        uf=place.uf,
        codigo=place.codigo,
        nome=place.nome,
        cargo=cargo,
        partido=party.partido,
        votos_nominais=party.votos_nominais,
        votos_legenda=party.votos_legenda,
    )


def _ballot(
    ano: int,
    turno: int,
    place: MunicipalPlace,
    cargo: str,
    tally: CargoTally,
) -> PresidentGovernorBallot:
    return PresidentGovernorBallot(
        ano=ano,
        turno=turno,
        uf=place.uf,
        codigo=place.codigo,
        cargo=cargo,
        branco=tally.branco,
        nulo=tally.nulo,
    )


def _line_rows(lines: tuple[PresidentGovernorLine, ...]) -> tuple[tuple[object, ...], ...]:
    return tuple(_line_row(line) for line in lines)


def _ballot_rows(ballots: tuple[PresidentGovernorBallot, ...]) -> tuple[tuple[object, ...], ...]:
    return tuple(_ballot_row(ballot) for ballot in ballots)


def _line_row(line: PresidentGovernorLine) -> tuple[object, ...]:
    return (
        line.uf,
        line.codigo,
        line.nome,
        line.cargo,
        line.partido,
        line.votos_nominais,
        line.votos_legenda,
    )


def _ballot_row(ballot: PresidentGovernorBallot) -> tuple[object, ...]:
    return (ballot.uf, ballot.codigo, ballot.cargo, ballot.branco, ballot.nulo)


class _Bucket:
    def __init__(self, uf: str, codigo: str, nome: str) -> None:
        self.uf = uf
        self.codigo = codigo
        self.nome = nome
        self.president: list[PartyTally] = []
        self.governor: list[PartyTally] = []
        self.president_blank: tuple[int, int] | None = None
        self.governor_blank: tuple[int, int] | None = None

    def add_party(self, cargo: str, party: PartyTally) -> None:
        if cargo == _PRESIDENT:
            self.president.append(party)
            return
        if cargo == _GOVERNOR:
            self.governor.append(party)
            return
        raise ElectionError(_BROKEN)

    def add_blank(self, cargo: str, branco: int, nulo: int) -> None:
        if cargo == _PRESIDENT:
            self.president_blank = (branco, nulo)
            return
        if cargo == _GOVERNOR:
            self.governor_blank = (branco, nulo)
            return
        raise ElectionError(_BROKEN)


def _places(
    lines: tuple[tuple[object, ...], ...],
    cedulas: tuple[tuple[object, ...], ...],
) -> tuple[MunicipalPlace, ...]:
    grouped: dict[tuple[str, str], _Bucket] = {}
    order: list[tuple[str, str]] = []
    for line in lines:
        _add_line(grouped, order, line)
    for cedula in cedulas:
        _add_cedula(grouped, cedula)
    return tuple(_finish(grouped[key]) for key in order)


def _add_line(
    grouped: dict[tuple[str, str], _Bucket],
    order: list[tuple[str, str]],
    row: tuple[object, ...],
) -> None:
    uf, codigo, nome, cargo, party = _parsed_line(row)
    key = (uf, codigo)
    bucket = grouped.get(key)
    if bucket is None:
        bucket = _Bucket(uf, codigo, nome)
        grouped[key] = bucket
        order.append(key)
    elif bucket.nome != nome:
        raise ElectionError(_BROKEN)
    bucket.add_party(cargo, party)


def _add_cedula(grouped: dict[tuple[str, str], _Bucket], row: tuple[object, ...]) -> None:
    uf, codigo, cargo, branco, nulo = _parsed_cedula(row)
    bucket = grouped.get((uf, codigo))
    if bucket is None:
        raise ElectionError(_BROKEN)
    bucket.add_blank(cargo, branco, nulo)


def _finish(bucket: _Bucket) -> MunicipalPlace:
    president = _required_cargo(bucket.president, bucket.president_blank)
    governor = _optional_cargo(bucket.governor, bucket.governor_blank)
    return MunicipalPlace(bucket.uf, bucket.codigo, bucket.nome, president, governor)


def _required_cargo(parties: list[PartyTally], blank: tuple[int, int] | None) -> CargoTally:
    if not parties or blank is None:
        raise ElectionError(_BROKEN)
    return CargoTally(tuple(parties), blank[0], blank[1])


def _optional_cargo(
    parties: list[PartyTally],
    blank: tuple[int, int] | None,
) -> CargoTally | None:
    if not parties and blank is None:
        return None
    if not parties or blank is None:
        raise ElectionError(_BROKEN)
    return CargoTally(tuple(parties), blank[0], blank[1])


def _parsed_line(row: tuple[object, ...]) -> tuple[str, str, str, str, PartyTally]:
    if len(row) != _LINE_WIDTH:
        raise ElectionError(_BROKEN)
    return (_text(row[0]), _text(row[1]), _text(row[2]), _text(row[3]), _party(row))


def _party(row: tuple[object, ...]) -> PartyTally:
    return PartyTally(_count(row[4]), _count(row[5]), _count(row[6]))


def _parsed_cedula(row: tuple[object, ...]) -> tuple[str, str, str, int, int]:
    if len(row) != _CEDULA_WIDTH:
        raise ElectionError(_BROKEN)
    return (_text(row[0]), _text(row[1]), _text(row[2]), _count(row[3]), _count(row[4]))


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ElectionError(_BROKEN)
    return value


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ElectionError(_BROKEN)
    return value
