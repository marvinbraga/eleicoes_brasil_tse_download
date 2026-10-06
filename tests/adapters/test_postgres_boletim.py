from collections.abc import Sequence

import pytest
from tests.boletim_fakes import bulletin, nominal_line

from eleicoes.adapters.postgres_boletim import PostgresBoletimSink
from eleicoes.adapters.postgres_sink import connect_postgres
from eleicoes.domain.errors import DatabaseConfigError
from eleicoes.domain.values import ElectionYear, Turno, Uf


def test_ensure_model_adds_boletim_without_dropping_correspondence() -> None:
    connection = _Connection()
    PostgresBoletimSink(lambda: connection).ensure_model()
    text = "\n".join(statement for statement, _params in connection.cursor_obj.statements)
    assert "CREATE TABLE IF NOT EXISTS raw.csec" in text
    assert "CREATE TABLE IF NOT EXISTS raw.ccont" in text
    assert "CREATE TABLE IF NOT EXISTS raw.boletim" in text
    assert "boletim_uf_cargo_numero_idx" in text
    assert "boletim_secao_idx" in text
    assert "COALESCE(partido, -1)" in text
    assert "DROP TABLE" not in text


def test_replace_deletes_only_the_requested_uf_and_copies_nulls() -> None:
    connection = _Connection()
    sink = PostgresBoletimSink(lambda: connection)
    lines = (
        nominal_line(comparecimento_cargo=2, quantidade=1),
        nominal_line(
            tipo_voto="branco",
            partido=None,
            numero=None,
            comparecimento_cargo=2,
            quantidade=1,
        ),
    )
    item = bulletin(votos=lines)
    inserted = sink.replace_uf(ElectionYear(2026), Turno(1), Uf("AC"), (item,))
    sink.replace_uf(ElectionYear(2026), Turno(1), Uf("AL"), (item,))
    assert inserted == 2
    deletes = [
        params for statement, params in connection.cursor_obj.statements if "DELETE" in statement
    ]
    assert deletes == [(2026, 1, "AC"), (2026, 1, "AL")]
    assert connection.cursor_obj.copies[0].count(b"\n") == 2
    assert connection.cursor_obj.copies[1].count(b"\n") == 2
    fields = connection.cursor_obj.copies[0].split(b"\n")[0].split(b"\t")
    assert len(fields) == 29
    assert b"\\N" in connection.cursor_obj.copies[0]
    assert b"branco" in connection.cursor_obj.copies[0]
    sink.close()
    assert connection.closed is True


def test_replace_without_votes_only_deletes_the_scope() -> None:
    connection = _Connection()
    sink = PostgresBoletimSink(lambda: connection)
    inserted = sink.replace_uf(ElectionYear(2024), Turno(2), Uf("RR"), (bulletin(votos=()),))
    assert inserted == 0
    assert connection.cursor_obj.copies == []
    statement, params = connection.cursor_obj.statements[0]
    assert statement == "DELETE FROM raw.boletim WHERE ano = %s AND turno = %s AND uf = %s"
    assert params == (2024, 2, "RR")


def test_missing_database_settings_fail_before_a_socket() -> None:
    sink = PostgresBoletimSink(lambda: connect_postgres({}))
    with pytest.raises(DatabaseConfigError):
        sink.ensure_model()


class _Copy:
    def __init__(self, store: list[bytes]) -> None:
        self._store = store

    def write(self, data: bytes) -> None:
        self._store.append(data)

    def __enter__(self) -> "_Copy":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Cursor:
    def __init__(self) -> None:
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.copies: list[bytes] = []
        self.rowcount = 0

    def execute(self, query: str, params: Sequence[object] | None = None) -> None:
        self.statements.append((query, tuple(params or ())))

    def copy(self, statement: str) -> _Copy:
        self.statements.append((statement, ()))
        return _Copy(self.copies)

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Connection:
    def __init__(self) -> None:
        self.cursor_obj = _Cursor()
        self.closed = False

    def cursor(self) -> _Cursor:
        return self.cursor_obj

    def transaction(self) -> "_Connection":
        return self

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *args: object) -> None:
        return None
