"""Municipality names against a fake cursor. No database."""

from collections.abc import Sequence

import pytest

from eleicoes.adapters.postgres_municipio import PostgresMunicipalityNames
from eleicoes.domain.errors import InvalidBoletimConsultaError


def test_padded_codes_become_ints_and_blank_names_are_skipped() -> None:
    connection = _Connection(
        [
            ("01007", " Xapuri "),
            ("01007", "Xapuri"),
            ("00100", " "),
            ("00100", ""),
            ("01392", "Rio Branco"),
            (1120, "Brasiléia"),
        ]
    )
    reader = PostgresMunicipalityNames(lambda: connection)
    assert reader.names("ac") == {1007: "Xapuri", 1392: "Rio Branco", 1120: "Brasiléia"}
    sql, params = connection.statements[0]
    assert sql == "SELECT cd_municipio, nm_municipio FROM raw.csec WHERE sg_uf = %s"
    assert params == ("AC",)
    assert "AC" not in sql


def test_two_names_for_one_code_are_rejected() -> None:
    rows = [("01007", "Xapuri"), ("01007", "Outro")]
    reader = PostgresMunicipalityNames(lambda: _Connection(rows))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.names("AC")


def test_bad_rows_are_rejected() -> None:
    reader = PostgresMunicipalityNames(lambda: _Connection([("01007",)]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.names("AC")
    reader = PostgresMunicipalityNames(lambda: _Connection([("abc", "Xapuri")]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.names("AC")
    reader = PostgresMunicipalityNames(lambda: _Connection([(True, "Xapuri")]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.names("AC")
    reader = PostgresMunicipalityNames(lambda: _Connection([("01007", None)]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.names("AC")


def test_connection_is_reused_and_closed_once() -> None:
    connection = _Connection([])
    calls = {"opened": 0}

    def connect() -> _Connection:
        calls["opened"] += 1
        return connection

    reader = PostgresMunicipalityNames(connect)
    reader.close()
    reader.names("AC")
    reader.names("AC")
    reader.close()
    reader.close()
    assert calls["opened"] == 1
    assert connection.closed == 1


class _Cursor:
    def __init__(
        self,
        rows: list[tuple[object, ...]],
        statements: list[tuple[str, tuple[object, ...]]],
    ) -> None:
        self._rows = rows
        self._statements = statements

    def execute(self, query: str, params: Sequence[object] | None = None) -> None:
        self._statements.append((query, tuple(params or ())))

    def fetchall(self) -> list[tuple[object, ...]]:
        return list(self._rows)

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Connection:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self._rows = rows
        self.closed = 0

    def cursor(self) -> _Cursor:
        return _Cursor(self._rows, self.statements)

    def transaction(self) -> "_Connection":
        return self

    def close(self) -> None:
        self.closed += 1

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *args: object) -> None:
        return None
