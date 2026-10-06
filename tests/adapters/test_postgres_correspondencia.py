"""Postgres correspondence reader against a fake cursor. No database."""

from collections.abc import Sequence
from datetime import datetime

import pytest

from eleicoes.adapters.postgres_correspondencia import PostgresCorrespondenciaReader
from eleicoes.domain.correspondencia import StatusCorrespondencia
from eleicoes.domain.errors import (
    InvalidCorrespondenceRecordError,
    UnknownCorrespondenceStatusError,
)

_WHEN = datetime(2026, 10, 4, 12, 59)
_CARGA = datetime(2026, 9, 24, 9, 5)


def test_latest_section_query_binds_filters_and_maps_a_new_section() -> None:
    connection = _Connection([_secao_row()])
    reader = PostgresCorrespondenciaReader(lambda: connection)
    secoes = reader.secoes("AC' OR '1'='1", StatusCorrespondencia.NOVA)
    sql, params = connection.cursor_obj.statements[0]
    assert "DISTINCT ON" in sql
    assert "to_timestamp" in sql
    assert "raw.csec" in sql
    assert "AC' OR '1'='1" not in sql
    assert "2269941" not in sql
    assert params == ("AC' OR '1'='1", "AC' OR '1'='1", "*", "*")
    assert secoes[0].status is StatusCorrespondencia.NOVA
    assert secoes[0].codigo_municipio == "01392"
    assert secoes[0].zona == 8
    assert secoes[0].numero == 3
    assert secoes[0].carga_em == _CARGA
    assert secoes[0].geracao_em == _WHEN


def test_optional_filters_are_bound_as_null_and_blank_dates_are_empty() -> None:
    row = _secao_row(status="S", carga_em="#NULO", zona=8, maquina=None)
    connection = _Connection([row])
    reader = PostgresCorrespondenciaReader(lambda: connection)
    secoes = reader.secoes(None, None)
    _sql, params = connection.cursor_obj.statements[0]
    assert params == (None, None, None, None)
    assert secoes[0].status is StatusCorrespondencia.ALTERADA
    assert secoes[0].carga_em is None
    assert secoes[0].maquina_geracao == ""
    assert secoes[0].zona == 8


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-09-24 09:05:00.100000", datetime(2026, 9, 24, 9, 5, 0, 100000)),
        ("24/09/2026 09:05:00", datetime(2026, 9, 24, 9, 5)),
        ("24/09/2026", datetime(2026, 9, 24)),
        ("", None),
        ("-1", None),
        ("  #NE  ", None),
        (_CARGA, _CARGA),
    ],
)
def test_carga_timestamps_and_sentinels(raw: object, expected: datetime | None) -> None:
    connection = _Connection([_secao_row(carga_em=raw)])
    reader = PostgresCorrespondenciaReader(lambda: connection)
    assert reader.secoes("AC", None)[0].carga_em == expected


def test_bad_rows_are_rejected() -> None:
    reader = PostgresCorrespondenciaReader(lambda: _Connection([_secao_row(status="Q")]))
    with pytest.raises(UnknownCorrespondenceStatusError):
        reader.secoes("AC", None)
    reader = PostgresCorrespondenciaReader(lambda: _Connection([("AC",)]))
    with pytest.raises(InvalidCorrespondenceRecordError):
        reader.secoes("AC", None)
    reader = PostgresCorrespondenciaReader(lambda: _Connection([_secao_row(zona=True)]))
    with pytest.raises(InvalidCorrespondenceRecordError):
        reader.secoes("AC", None)
    reader = PostgresCorrespondenciaReader(lambda: _Connection([_secao_row(zona="zona")]))
    with pytest.raises(InvalidCorrespondenceRecordError):
        reader.secoes("AC", None)
    reader = PostgresCorrespondenciaReader(lambda: _Connection([_secao_row(municipio=1)]))
    with pytest.raises(InvalidCorrespondenceRecordError):
        reader.secoes("AC", None)
    reader = PostgresCorrespondenciaReader(lambda: _Connection([_secao_row(carga_em=1)]))
    with pytest.raises(InvalidCorrespondenceRecordError):
        reader.secoes("AC", None)
    reader = PostgresCorrespondenciaReader(lambda: _Connection([_secao_row(carga_em="ontem")]))
    with pytest.raises(InvalidCorrespondenceRecordError):
        reader.secoes("AC", None)
    reader = PostgresCorrespondenciaReader(lambda: _Connection([_secao_row(geracao_em="hoje")]))
    with pytest.raises(InvalidCorrespondenceRecordError):
        reader.secoes("AC", None)


def test_contingency_query_binds_the_uf_and_maps_a_new_urn() -> None:
    connection = _Connection([_contingencia_row()])
    reader = PostgresCorrespondenciaReader(lambda: connection)
    urns = reader.contingencias("AC", StatusCorrespondencia.NOVA)
    sql, params = connection.cursor_obj.statements[0]
    assert "DISTINCT ON" in sql
    assert "to_timestamp" in sql
    assert "raw.ccont" in sql
    assert "nr_urna_esperada" in sql
    assert "AC" not in sql
    assert params == ("AC", "AC", "*", "*")
    assert urns[0].status is StatusCorrespondencia.NOVA
    assert urns[0].urna_esperada == "2269941"
    assert not hasattr(urns[0], "numero")


def test_summary_query_is_an_aggregate_and_counts_arrive_as_text() -> None:
    connection = _Connection([("AC", "10", "2", 3, "4", "1", "0", "5", "1")])
    reader = PostgresCorrespondenciaReader(lambda: connection)
    resumos = reader.resumos()
    sql, params = connection.cursor_obj.statements[0]
    assert "DISTINCT ON" in sql
    assert "to_timestamp" in sql
    assert "count(" in sql
    assert "GROUP BY" in sql
    assert params == ()
    assert resumos[0].uf == "AC"
    assert resumos[0].secoes == 10
    assert resumos[0].zonas == 3
    assert resumos[0].contingencias_novas == 1


def test_changes_query_keeps_only_a_real_difference() -> None:
    anterior = datetime(2026, 10, 3, 15, 34)
    row = (
        "AC",
        "01392",
        "RIO BRANCO",
        "8",
        "3",
        anterior,
        _WHEN,
        "1",
        "2",
        "A",
        "A",
        "AA",
        "BB",
        "10",
        "10",
        "M1",
        "M1",
    )
    connection = _Connection([row])
    reader = PostgresCorrespondenciaReader(lambda: connection)
    changes = reader.mudancas(None)
    sql, params = connection.cursor_obj.statements[0]
    assert "row_number" in sql
    assert "to_timestamp" in sql
    assert "IS DISTINCT FROM" in sql
    assert params == (None, None)
    assert changes[0].campos_alterados == ("urna", "flashcard")
    assert changes[0].geracao_anterior == anterior


def test_generations_bind_zone_and_section() -> None:
    connection = _Connection([_secao_row(status="N")])
    reader = PostgresCorrespondenciaReader(lambda: connection)
    rows = reader.geracoes("AC", 4321, 15)
    sql, params = connection.cursor_obj.statements[0]
    assert "to_timestamp" in sql
    assert "ASC" in sql
    assert "4321" not in sql
    assert "15" not in sql
    assert params == ("AC", 4321, 4321, 15, 15)
    assert rows[0].status is StatusCorrespondencia.NAO_ALTERADA


def test_projections_map_the_latest_status_code() -> None:
    connection = _Connection(
        [
            ("ac", "01392", "RIO BRANCO", "8", "3", "1", "CARGA", "FA10805F", "*", "MAQ"),
        ]
    )
    reader = PostgresCorrespondenciaReader(lambda: connection)
    projections = reader.projecoes("AC")
    sql, _params = connection.cursor_obj.statements[0]
    assert "DISTINCT ON" in sql
    assert "to_timestamp" in sql
    assert "st_corresp_alterada" in sql
    assert projections[0].status is StatusCorrespondencia.NOVA
    assert projections[0].uf == "AC"
    assert projections[0].secao == 3
    connection.cursor_obj.rows = [("AC", "01392", "RIO BRANCO", "9", "55", "*")]
    contingencias = reader.projecoes_contingencia(None)
    assert contingencias[0].status is StatusCorrespondencia.NOVA
    assert contingencias[0].urna == "55"
    assert connection.cursor_obj.statements[1][1] == (None, None)


def test_connection_is_reused_and_a_second_close_is_safe() -> None:
    connection = _Connection([])
    opens: list[int] = []

    def connect() -> _Connection:
        opens.append(1)
        return connection

    reader = PostgresCorrespondenciaReader(connect)
    reader.close()
    assert opens == []
    assert reader.resumos() == ()
    assert reader.resumos() == ()
    assert opens == [1]
    reader.close()
    reader.close()
    assert connection.closed == 1


def _secao_row(
    *,
    zona: object = "8",
    status: object = "*",
    carga_em: object = "2026-09-24 09:05:00",
    municipio: object = "RIO BRANCO",
    geracao_em: object = _WHEN,
    maquina: object = "MAQ",
) -> tuple[object, ...]:
    return (
        "AC",
        "01392",
        municipio,
        zona,
        "3",
        "1104",
        "2269941",
        "CARGA",
        "FA10805F",
        carga_em,
        status,
        maquina,
        "TPM",
        "INST",
        "MAQ2",
        "TPM2",
        "INST2",
        geracao_em,
    )


def _contingencia_row() -> tuple[object, ...]:
    return (
        "AC",
        "01392",
        "RIO BRANCO",
        "8",
        "2269941",
        "CARGA",
        "FA10805F",
        None,
        "*",
        "MAQ",
        "TPM",
        "INST",
        "MAQ2",
        "TPM2",
        "INST2",
        _WHEN,
    )


class _Cursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.rowcount = 0

    def execute(self, query: str, params: Sequence[object] | None = None) -> None:
        self.statements.append((query, tuple(params or ())))

    def fetchall(self) -> list[tuple[object, ...]]:
        return list(self.rows)

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Connection:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.cursor_obj = _Cursor(rows)
        self.closed = 0

    def cursor(self) -> _Cursor:
        return self.cursor_obj

    def transaction(self) -> "_Connection":
        return self

    def close(self) -> None:
        self.closed += 1

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *args: object) -> None:
        return None
