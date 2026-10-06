"""Reads municipality names from raw.csec. User values are bound, never interpolated."""

from collections.abc import Mapping, Sequence
from typing import Final

from eleicoes.adapters.postgres_sink import ConnectionFactory, SqlConnection
from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.values import Uf

_WIDTH: Final = 2
_NAMES: Final = "SELECT cd_municipio, nm_municipio FROM raw.csec WHERE sg_uf = %s"


class PostgresMunicipalityNames:
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect
        self._connection: SqlConnection | None = None

    def names(self, uf: str) -> Mapping[int, str]:
        rows = self._rows(_NAMES, (Uf(uf).code,))
        return _names(rows)

    def close(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            connection.close()

    def _rows(self, sql: str, params: Sequence[object]) -> tuple[tuple[object, ...], ...]:
        connection = self._open()
        with connection.transaction(), connection.cursor() as cursor:
            cursor.execute(sql, params)
            return tuple(tuple(row) for row in cursor.fetchall())

    def _open(self) -> SqlConnection:
        if self._connection is None:
            self._connection = self._connect()
        return self._connection


def _names(rows: tuple[tuple[object, ...], ...]) -> dict[int, str]:
    found: dict[int, str] = {}
    for row in rows:
        if len(row) != _WIDTH:
            raise InvalidBoletimConsultaError("municipio")
        code = _code(row[0])
        label = _label(row[1])
        if label is None:
            continue
        previous = found.get(code)
        if previous is not None and previous != label:
            raise InvalidBoletimConsultaError("municipio")
        found[code] = label
    return found


def _code(value: object) -> int:
    if isinstance(value, bool):
        raise InvalidBoletimConsultaError("municipio")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise InvalidBoletimConsultaError("municipio")


def _label(value: object) -> str | None:
    if not isinstance(value, str):
        raise InvalidBoletimConsultaError("municipio")
    stripped = value.strip()
    if stripped == "":
        return None
    return stripped
