"""Candidate vote scan against a fake cursor. No database."""

from collections.abc import Sequence

import psycopg
import pytest

from eleicoes.adapters.postgres_votos_candidato import PostgresCandidateVotes
from eleicoes.domain.errors import ElectionError, InvalidBoletimConsultaError, InvalidCargoError
from eleicoes.domain.simulacao_cadeiras import VotoApurado


class _Cursor:
    def __init__(self, rows: list[tuple[object, ...]], log: list[tuple[str, tuple[object, ...]]]):
        self._rows = rows
        self._log = log

    def execute(self, query: str, params: Sequence[object] | None = None) -> None:
        self._log.append((query, tuple(params or ())))

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._rows

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _Connection:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.rows = rows
        self.closed = 0

    def cursor(self) -> _Cursor:
        return _Cursor(self.rows, self.statements)

    def transaction(self) -> "_Connection":
        return self

    def close(self) -> None:
        self.closed += 1

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_one_grouped_scan_per_cargo_with_bound_parameters() -> None:
    connection = _Connection([("AC", "nominal", 1301, 250), ("AC", "legenda", 13, 10)])
    source = PostgresCandidateVotes(lambda: connection)  # type: ignore[arg-type,return-value]
    found = source.candidate_totals(2026, 1, "deputadoFederal")
    assert found == (
        VotoApurado("deputadoFederal", "AC", "nominal", 1301, 250),
        VotoApurado("deputadoFederal", "AC", "legenda", 13, 10),
    )
    sql, params = connection.statements[0]
    assert "SUM(quantidade)" in sql
    assert "GROUP BY uf, tipo_voto, numero" in sql
    assert "tipo_voto IN ('nominal', 'legenda')" in sql
    assert params == (2026, 1, "deputadoFederal")
    source.close()
    source.close()
    assert connection.closed == 1


@pytest.mark.parametrize(
    "row",
    [("AC", "nominal", "1301", 1), ("AC", "nominal", 1301, True), ("AC", "nominal", 1301)],
)
def test_bad_rows_are_rejected(row: tuple[object, ...]) -> None:
    source = PostgresCandidateVotes(lambda: _Connection([row]))  # type: ignore[arg-type,return-value]
    with pytest.raises(InvalidBoletimConsultaError):
        source.candidate_totals(2026, 1, "deputadoFederal")


def test_blank_cargo_is_refused_before_the_query() -> None:
    connection = _Connection([])
    with pytest.raises(InvalidCargoError):
        PostgresCandidateVotes(lambda: connection).candidate_totals(2026, 1, " ")  # type: ignore[arg-type,return-value]
    assert connection.statements == []


def test_driver_errors_become_election_errors() -> None:
    def broken() -> _Connection:
        raise psycopg.OperationalError("down")

    source = PostgresCandidateVotes(broken)  # type: ignore[arg-type]
    with pytest.raises(ElectionError, match="candidate vote scan failed"):
        source.candidate_totals(2026, 1, "deputadoFederal")
