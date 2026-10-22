"""PostgresMunicipalStore against a scripted cursor. No database socket."""

from collections.abc import Sequence
from datetime import date, datetime

import pytest

from eleicoes.adapters.postgres_municipais import PostgresMunicipalStore
from eleicoes.domain.errors import InvalidMunicipalRowError
from eleicoes.domain.municipais import (
    CandidateRow,
    CouncilSeats,
    ElectorateRow,
    Mayor,
    MunicipalBuild,
    MunicipalityResult,
    SeatRow,
)

_CANDIDATE = (
    "MG",
    "45616",
    "GUAPÉ",
    "1",
    "06/07/2025",
    "1",
    "11",
    "13",
    "DR PEDRO",
    "22",
    "PL",
    "1",
)
_ELECTORATE = ("MG", "45616", "GUAPÉ", "2", "1", "11", "12000")
_SEAT = ("MG", "45616", "2", "13", "9")


class _Copy:
    def __init__(self, cursor: "_Cursor", statement: str) -> None:
        self._cursor = cursor
        self._statement = statement

    def write(self, data: bytes) -> None:
        self._cursor.copied.append((self._statement, data.decode("utf-8")))

    def __enter__(self) -> "_Copy":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Cursor:
    def __init__(self, connection: "_Connection") -> None:
        self._connection = connection
        self.rowcount = 0
        self.copied: list[tuple[str, str]] = []

    def execute(self, query: str, params: Sequence[object] | None = None) -> None:
        self._connection.log.append((query, tuple(params or ()), self._connection.depth))

    def fetchall(self) -> Sequence[Sequence[object]]:
        return self._connection.batches.pop(0)

    def copy(self, statement: str) -> _Copy:
        self._connection.log.append((statement, (), self._connection.depth))
        return _Copy(self, statement)

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Transaction:
    def __init__(self, connection: "_Connection") -> None:
        self._connection = connection

    def __enter__(self) -> object:
        self._connection.depth += 1
        return self

    def __exit__(self, *args: object) -> None:
        self._connection.depth -= 1


class _Connection:
    def __init__(self, *batches: Sequence[Sequence[object]]) -> None:
        self.batches = list(batches)
        self.log: list[tuple[str, tuple[object, ...], int]] = []
        self.depth = 0
        self.closed = False
        self.cursor_obj = _Cursor(self)

    def cursor(self) -> _Cursor:
        return self.cursor_obj

    def transaction(self) -> _Transaction:
        return _Transaction(self)

    def close(self) -> None:
        self.closed = True


def _store(connection: _Connection) -> PostgresMunicipalStore:
    return PostgresMunicipalStore(lambda: connection)


def test_read_raw_binds_the_year_as_text_and_parses_the_rows() -> None:
    connection = _Connection(
        [(datetime(2026, 10, 22, 2, 17),)], [_CANDIDATE], [_ELECTORATE], [_SEAT]
    )
    raw = _store(connection).read_raw(2024)
    assert [params for _sql, params, _depth in connection.log] == [("2024",)] * 4
    assert all(depth == 1 for _sql, _params, depth in connection.log)
    assert raw.geracao == "221020260217"
    assert raw.candidatos == (
        CandidateRow(
            "MG", "45616", "GUAPÉ", 1, date(2025, 7, 6), 1, 11, "13", "DR PEDRO", 22, "PL", 1
        ),
    )
    assert raw.eleitorado == (ElectorateRow("MG", "45616", "GUAPÉ", 2, 1, 11, 12000),)
    assert raw.vagas == (SeatRow("MG", "45616", 2, 13, 9),)


def test_read_raw_filters_only_what_the_rule_never_uses() -> None:
    connection = _Connection([(datetime(2026, 10, 22, 2, 17),)], [], [], [])
    _store(connection).read_raw(2024)
    sql = [query for query, _params, _depth in connection.log]
    assert "FROM raw.consulta_cand" in sql[1] and "cd_cargo IN ('11', '13')" in sql[1]
    assert "FROM raw.detalhe_votacao_munzona" in sql[2] and "cd_cargo = '11'" in sql[2]
    assert "FROM raw.consulta_vagas" in sql[3] and "cd_cargo = '13'" in sql[3]


def test_null_party_number_is_an_invalid_row() -> None:
    bad = (*_CANDIDATE[:9], "#NULO", *_CANDIDATE[10:])
    connection = _Connection([(datetime(2026, 10, 22, 2, 17),)], [bad], [], [])
    with pytest.raises(InvalidMunicipalRowError) as caught:
        _store(connection).read_raw(2024)
    assert caught.value.field == "nr_partido"


@pytest.mark.parametrize("value", [None, "22/10/2026"])
def test_missing_generation_is_an_invalid_row(value: object) -> None:
    connection = _Connection([(value,)])
    with pytest.raises(InvalidMunicipalRowError) as caught:
        _store(connection).read_raw(2024)
    assert caught.value.field == "geracao"


def test_non_text_value_is_an_invalid_row() -> None:
    bad = (*_ELECTORATE[:6], 12000)
    connection = _Connection([(datetime(2026, 10, 22, 2, 17),)], [], [bad], [])
    with pytest.raises(InvalidMunicipalRowError) as caught:
        _store(connection).read_raw(2024)
    assert caught.value.field == "qt_aptos"


def _built() -> MunicipalBuild:
    mayor = Mayor(22, "PL", "DR PEDRO", "13", date(2025, 7, 6), 1, True)
    return MunicipalBuild(
        "221020260217",
        (
            MunicipalityResult("MG", "45616", "GUAPÉ", 12000, 9, mayor),
            MunicipalityResult("MG", "48313", "MERCÊS", 9000, 9, None),
        ),
        (CouncilSeats("MG", "45616", 22, "PL", 4),),
        (),
    )


def test_save_replaces_the_year_in_one_transaction() -> None:
    connection = _Connection()
    _store(connection).save(2024, _built())
    statements = [(sql.split(" (")[0], params, depth) for sql, params, depth in connection.log]
    assert statements == [
        ("DELETE FROM analise.municipal_carga WHERE ano = %s", (2024,), 1),
        ("INSERT INTO analise.municipal_carga", (2024, "221020260217", 2, 1, 4, 0), 1),
        ("COPY analise.municipal_prefeito", (), 1),
        ("COPY analise.municipal_vereador", (), 1),
    ]


def test_save_writes_empty_fields_for_a_municipality_without_mayor() -> None:
    connection = _Connection()
    _store(connection).save(2024, _built())
    copied = dict(connection.cursor_obj.copied)
    mayors = next(text for sql, text in copied.items() if "municipal_prefeito" in sql)
    council = next(text for sql, text in copied.items() if "municipal_vereador" in sql)
    assert mayors.splitlines() == [
        "2024,MG,45616,GUAPÉ,12000,9,22,PL,DR PEDRO,13,2025-07-06,1,t",
        "2024,MG,48313,MERCÊS,9000,9,,,,,,,f",
    ]
    assert council.splitlines() == ["2024,MG,45616,22,PL,4"]
    assert all("(FORMAT CSV)" in sql for sql in copied)


def test_close_reuses_and_then_releases_the_connection() -> None:
    connection = _Connection([(datetime(2026, 10, 22, 2, 17),)], [], [], [])
    opened: list[_Connection] = []

    def connect() -> _Connection:
        opened.append(connection)
        return connection

    store = PostgresMunicipalStore(connect)
    store.read_raw(2024)
    store.save(2024, _built())
    store.close()
    store.close()
    assert len(opened) == 1
    assert connection.closed is True
