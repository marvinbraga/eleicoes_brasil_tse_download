"""Sums raw.boletim per UF and candidate number, one sequential scan per cargo."""

from collections.abc import Sequence
from typing import Final

import psycopg

from eleicoes.adapters.postgres_sink import ConnectionFactory, SqlConnection
from eleicoes.domain.boletim_consulta import require_cargo
from eleicoes.domain.errors import ElectionError, InvalidBoletimConsultaError
from eleicoes.domain.simulacao_cadeiras import VotoApurado
from eleicoes.domain.values import ElectionYear, Turno

_WIDTH: Final = 4
_FAILED: Final = "candidate vote scan failed"
_TOTALS: Final = """
SELECT uf, tipo_voto, numero, SUM(quantidade)::bigint AS votos
FROM raw.boletim
WHERE ano = %s
  AND turno = %s
  AND cargo = %s
  AND tipo_voto IN ('nominal', 'legenda')
  AND numero IS NOT NULL
GROUP BY uf, tipo_voto, numero
ORDER BY uf, tipo_voto, numero
"""


class PostgresCandidateVotes:
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect
        self._connection: SqlConnection | None = None

    def candidate_totals(self, ano: int, turno: int, cargo: str) -> tuple[VotoApurado, ...]:
        params = (ElectionYear(ano).value, Turno(turno).value, require_cargo(cargo))
        try:
            connection = self._open()
            with connection.transaction(), connection.cursor() as cursor:
                cursor.execute(_TOTALS, params)
                rows = tuple(tuple(row) for row in cursor.fetchall())
        except psycopg.Error as exc:
            raise ElectionError(_FAILED) from exc
        return tuple(_vote(cargo, row) for row in rows)

    def close(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            connection.close()

    def _open(self) -> SqlConnection:
        if self._connection is None:
            self._connection = self._connect()
        return self._connection


def _vote(cargo: str, row: Sequence[object]) -> VotoApurado:
    if len(row) != _WIDTH:
        raise InvalidBoletimConsultaError(row)
    uf, tipo, numero, votos = row
    if not isinstance(uf, str) or not isinstance(tipo, str):
        raise InvalidBoletimConsultaError(row)
    return VotoApurado(cargo, uf, tipo, _integer(numero), _integer(votos))


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidBoletimConsultaError(value)
    return value
