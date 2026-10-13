"""Guarda os votos municipais do cruzamento. A senha fica na fábrica de conexão."""

from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Final, TypeVar

import psycopg

from eleicoes.adapters.postgres_sink import ConnectionFactory, CursorWork, SqlConnection, SqlCursor
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport

_TABLES_SQL = (Path(__file__).resolve().parent / "sql" / "tables.sql").read_text(encoding="utf-8")
_LINE_WIDTH: Final = 7
_CEDULA_WIDTH: Final = 5
_PRESIDENT: Final = "presidente"
_GOVERNOR: Final = "governador"
_HEADER = (
    "INSERT INTO analise.relatorio_presidente_governador (ano, turno) "
    "VALUES (%s, %s) "
    "ON CONFLICT (ano, turno) DO UPDATE "
    "SET gerado_em = now() "
    "RETURNING gerado_em"
)
_DELETE_LINHA = (
    "DELETE FROM analise.relatorio_presidente_governador_linha WHERE ano = %s AND turno = %s"
)
_DELETE_CEDULA = (
    "DELETE FROM analise.relatorio_presidente_governador_cedula WHERE ano = %s AND turno = %s"
)
_INSERT_LINHA = (
    "INSERT INTO analise.relatorio_presidente_governador_linha ("
    "ano, turno, uf, codigo, nome, cargo, partido, votos_nominais, votos_legenda) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
_INSERT_CEDULA = (
    "INSERT INTO analise.relatorio_presidente_governador_cedula ("
    "ano, turno, uf, codigo, cargo, branco, nulo) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
_LOAD_HEADER = (
    "SELECT gerado_em FROM analise.relatorio_presidente_governador "
    "WHERE ano = %s AND turno = %s"
)
_LOAD_LINHA = (
    "SELECT uf, codigo, nome, cargo, partido, votos_nominais, votos_legenda "
    "FROM analise.relatorio_presidente_governador_linha "
    "WHERE ano = %s AND turno = %s"
)
_LOAD_CEDULA = (
    "SELECT uf, codigo, cargo, branco, nulo "
    "FROM analise.relatorio_presidente_governador_cedula "
    "WHERE ano = %s AND turno = %s"
)
_T = TypeVar("_T")


class PostgresPresidentGovernorStore:
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect
        self._connection: SqlConnection | None = None

    def ensure_model(self) -> None:
        self._run(lambda cursor: _execute_script(cursor, _TABLES_SQL))

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
        connection = self._connection
        self._connection = None
        if connection is not None:
            connection.close()

    def _load(self, ano: int, turno: int) -> StoredCrossReport | None:
        self.ensure_model()
        found: list[StoredCrossReport | None] = [None]

        def work(cursor: SqlCursor) -> None:
            found[0] = _read(cursor, ano, turno)

        self._run(work)
        return found[0]

    def _save(self, ano: int, turno: int, places: tuple[MunicipalPlace, ...]) -> datetime:
        self.ensure_model()
        found: list[datetime] = []

        def work(cursor: SqlCursor) -> None:
            found.append(_write(cursor, ano, turno, places))

        self._run(work)
        return found[0]

    def _guard(self, work: Callable[[], _T]) -> _T:
        try:
            return work()
        except ElectionError:
            raise
        except psycopg.Error as exc:
            raise ElectionError("cross report store failed") from exc

    def _run(self, work: CursorWork) -> None:
        connection = self._open()
        with connection.transaction(), connection.cursor() as cursor:
            work(cursor)

    def _open(self) -> SqlConnection:
        if self._connection is None:
            self._connection = self._connect()
        return self._connection


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
        raise ElectionError("cross report row is incomplete")

    def add_blank(self, cargo: str, branco: int, nulo: int) -> None:
        if cargo == _PRESIDENT:
            self.president_blank = (branco, nulo)
            return
        if cargo == _GOVERNOR:
            self.governor_blank = (branco, nulo)
            return
        raise ElectionError("cross report row is incomplete")


def _read(cursor: SqlCursor, ano: int, turno: int) -> StoredCrossReport | None:
    cursor.execute(_LOAD_HEADER, (ano, turno))
    header = _rows(cursor)
    if not header:
        return None
    lines = _fetch(cursor, _LOAD_LINHA, ano, turno)
    cedulas = _fetch(cursor, _LOAD_CEDULA, ano, turno)
    return StoredCrossReport(_places(lines, cedulas), _one_clock(header))


def _fetch(cursor: SqlCursor, query: str, ano: int, turno: int) -> tuple[tuple[object, ...], ...]:
    cursor.execute(query, (ano, turno))
    return _rows(cursor)


def _write(
    cursor: SqlCursor,
    ano: int,
    turno: int,
    places: tuple[MunicipalPlace, ...],
) -> datetime:
    cursor.execute(_HEADER, (ano, turno))
    moment = _returned(cursor)
    cursor.execute(_DELETE_LINHA, (ano, turno))
    cursor.execute(_DELETE_CEDULA, (ano, turno))
    for place in places:
        _insert_place(cursor, ano, turno, place)
    return moment


def _insert_place(cursor: SqlCursor, ano: int, turno: int, place: MunicipalPlace) -> None:
    _insert_cargo(cursor, ano, turno, place, _PRESIDENT, place.presidente)
    if place.governador is not None:
        _insert_cargo(cursor, ano, turno, place, _GOVERNOR, place.governador)


def _insert_cargo(
    cursor: SqlCursor,
    ano: int,
    turno: int,
    place: MunicipalPlace,
    cargo: str,
    tally: CargoTally,
) -> None:
    for party in tally.parties:
        cursor.execute(_INSERT_LINHA, _line(ano, turno, place, cargo, party))
    cursor.execute(_INSERT_CEDULA, _cedula_params(ano, turno, place, cargo, tally))


def _line(
    ano: int,
    turno: int,
    place: MunicipalPlace,
    cargo: str,
    party: PartyTally,
) -> tuple[object, ...]:
    return (
        ano,
        turno,
        place.uf,
        place.codigo,
        place.nome,
        cargo,
        party.partido,
        party.votos_nominais,
        party.votos_legenda,
    )


def _cedula_params(
    ano: int,
    turno: int,
    place: MunicipalPlace,
    cargo: str,
    tally: CargoTally,
) -> tuple[object, ...]:
    return (ano, turno, place.uf, place.codigo, cargo, tally.branco, tally.nulo)


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
        raise ElectionError("cross report row is incomplete")
    bucket.add_party(cargo, party)


def _add_cedula(grouped: dict[tuple[str, str], _Bucket], row: tuple[object, ...]) -> None:
    uf, codigo, cargo, branco, nulo = _parsed_cedula(row)
    bucket = grouped.get((uf, codigo))
    if bucket is None:
        raise ElectionError("cross report row is incomplete")
    bucket.add_blank(cargo, branco, nulo)


def _finish(bucket: _Bucket) -> MunicipalPlace:
    president = _required_cargo(bucket.president, bucket.president_blank)
    governor = _optional_cargo(bucket.governor, bucket.governor_blank)
    return MunicipalPlace(bucket.uf, bucket.codigo, bucket.nome, president, governor)


def _required_cargo(parties: list[PartyTally], blank: tuple[int, int] | None) -> CargoTally:
    if not parties or blank is None:
        raise ElectionError("cross report row is incomplete")
    return CargoTally(tuple(parties), blank[0], blank[1])


def _optional_cargo(
    parties: list[PartyTally],
    blank: tuple[int, int] | None,
) -> CargoTally | None:
    if not parties and blank is None:
        return None
    if not parties or blank is None:
        raise ElectionError("cross report row is incomplete")
    return CargoTally(tuple(parties), blank[0], blank[1])


def _parsed_line(row: tuple[object, ...]) -> tuple[str, str, str, str, PartyTally]:
    if len(row) != _LINE_WIDTH:
        raise ElectionError("cross report row is incomplete")
    return (_text(row[0]), _text(row[1]), _text(row[2]), _text(row[3]), _party(row))


def _party(row: tuple[object, ...]) -> PartyTally:
    return PartyTally(_count(row[4]), _count(row[5]), _count(row[6]))


def _parsed_cedula(row: tuple[object, ...]) -> tuple[str, str, str, int, int]:
    if len(row) != _CEDULA_WIDTH:
        raise ElectionError("cross report row is incomplete")
    return (_text(row[0]), _text(row[1]), _text(row[2]), _count(row[3]), _count(row[4]))


def _returned(cursor: SqlCursor) -> datetime:
    rows = _rows(cursor)
    return _one_clock(rows)


def _one_clock(rows: tuple[tuple[object, ...], ...]) -> datetime:
    if len(rows) != 1 or len(rows[0]) != 1:
        raise ElectionError("cross report was not stored")
    return _clock(rows[0][0])


def _rows(cursor: SqlCursor) -> tuple[tuple[object, ...], ...]:
    return tuple(tuple(row) for row in cursor.fetchall())


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ElectionError("cross report row is incomplete")
    return value


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ElectionError("cross report row is incomplete")
    return value


def _clock(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise ElectionError("cross report row is incomplete")
    return value


def _execute_script(cursor: SqlCursor, script: str) -> None:
    for statement in _statements(script):
        cursor.execute(statement)


def _statements(script: str) -> Iterator[str]:
    for chunk in script.split(";"):
        statement = chunk.strip()
        if statement:
            yield statement
