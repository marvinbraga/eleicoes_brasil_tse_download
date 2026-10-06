"""Postgres boletim reader against a fake cursor. No database."""

import re
from collections.abc import Sequence
from decimal import Decimal

import pytest

from eleicoes.adapters.postgres_boletim_consulta import PostgresBoletimReader
from eleicoes.domain.errors import InvalidBoletimConsultaError, InvalidNivelError


def test_sql_sums_quantidade_and_does_not_sum_comparecimento_cargo() -> None:
    connection = _Connection([])
    reader = PostgresBoletimReader(lambda: connection)
    reader.totals(2026, 1, "AC", "presidente")
    reader.municipalities(2026, 1, "AC", "presidente", 22)
    reader.comparison(2026, 1, "AC", "presidente", 22, 13, "municipio")
    reader.comparison(2026, 1, "AC", "presidente", 22, 13, "zona")
    reader.comparison(2026, 1, "AC", "presidente", 22, 13, "secao")
    reader.zones(2026, 1, "AC", 1120, "presidente", 22)
    reader.section_projections(2026, 1, "AC", "presidente")
    reader.nominal_projections(2026, 1, "AC", "presidente")
    reader.blank_projections(2026, 1, "AC", "presidente")
    reader.section_lines(2026, 1, "AC", 1120, 1, 2)
    text = "\n".join(statement for statement, _params in connection.statements)
    assert "SUM(quantidade)" in text
    assert "MAX(comparecimento_cargo)" in text
    assert "SUM(comparecimento_cargo)" not in text
    assert "2026" not in text
    assert "presidente" not in text
    ranking = connection.statements[1][0]
    assert "LEFT JOIN" in ranking
    assert "COALESCE(votos.quantidade, 0)" in ranking
    zones = connection.statements[5][0]
    assert "MAX(comparecimento_cargo)" in zones
    assert "SUM(quantidade)" in zones
    lines = connection.statements[-1][0]
    assert "SUM(" not in lines
    assert connection.statements[1][1] == (
        2026,
        1,
        "AC",
        "presidente",
        2026,
        1,
        "AC",
        "presidente",
        22,
    )
    municipio_sql = connection.statements[2][0]
    zona_sql = connection.statements[3][0]
    secao_sql = connection.statements[4][0]
    assert "SELECT municipio, SUM(comparecimento)" in municipio_sql
    assert "SELECT municipio, zona, SUM(comparecimento)" in zona_sql
    assert "SELECT municipio, zona, secao, SUM(comparecimento)" in secao_sql


def test_rows_map_text_integers_nulls_and_a_zero_comparison() -> None:
    reader = PostgresBoletimReader(
        lambda: _Connection([("nominal", "22", "22", "100"), ("branco", None, None, 4)])
    )
    totals = reader.totals(2026, 1, "AC", "presidente")
    assert totals[0].partido == 22
    assert totals[0].quantidade == 100
    assert totals[1].partido is None
    assert totals[1].numero is None

    reader = PostgresBoletimReader(lambda: _Connection([(1120, 0, 30)]))
    city = reader.municipalities(2026, 1, "AC", "presidente", 13)[0]
    assert city.quantidade == 0
    assert city.comparecimento == 30

    reader = PostgresBoletimReader(lambda: _Connection([(1120, 8, 4, 0, 15)]))
    side = reader.comparison(2026, 1, "AC", "presidente", 22, 13, "zona")[0]
    assert side.zona == 8
    assert side.secao is None
    assert side.votos_segundo == 0

    reader = PostgresBoletimReader(lambda: _Connection([(1120, 8, 3, 4, 0, 15)]))
    section = reader.comparison(2026, 1, "AC", "presidente", 22, 13, "secao")[0]
    assert (section.municipio, section.zona, section.secao) == (1120, 8, 3)

    reader = PostgresBoletimReader(lambda: _Connection([("presidente", 1, "nulo", None, None, 2)]))
    line = reader.section_lines(2026, 1, "AC", 1120, 8, 3)[0]
    assert line.tipo_voto == "nulo"
    assert line.quantidade == 2

    reader = PostgresBoletimReader(lambda: _Connection([(8, "0", 11)]))
    zone = reader.zones(2026, 1, "AC", 1120, "presidente", 22)[0]
    assert zone.quantidade == 0

    reader = PostgresBoletimReader(lambda: _Connection([(1120, 8, 3, 40, 80)]))
    projection = reader.section_projections(2026, 1, "AC", "senador")[0]
    assert projection.comparecimento == 40
    assert projection.quantidade == 80

    reader = PostgresBoletimReader(lambda: _Connection([(1120, 22, 9)]))
    nominal = reader.nominal_projections(2026, 1, "AC", "presidente")[0]
    assert nominal.numero == 22

    reader = PostgresBoletimReader(lambda: _Connection([(1120, 3)]))
    blank = reader.blank_projections(2026, 1, "AC", "presidente")[0]
    assert blank.quantidade == 3


def test_decimal_aggregates_map_to_ints() -> None:
    reader = PostgresBoletimReader(
        lambda: _Connection([(1392, Decimal("131895"), Decimal("0"), Decimal("200000"))])
    )
    side = reader.comparison(2026, 1, "AC", "presidente", 22, 13, "municipio")[0]
    assert (side.municipio, side.votos_primeiro, side.votos_segundo) == (1392, 131895, 0)
    assert side.comparecimento == 200000
    assert side.zona is None

    reader = PostgresBoletimReader(lambda: _Connection([(1392, Decimal("1.5"), 0, 2)]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.comparison(2026, 1, "AC", "presidente", 22, 13, "municipio")

    reader = PostgresBoletimReader(lambda: _Connection([(1392, Decimal("Infinity"), 0, 2)]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.comparison(2026, 1, "AC", "presidente", 22, 13, "municipio")

    reader = PostgresBoletimReader(lambda: _Connection([(1392, 1.5, 0, 2)]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.comparison(2026, 1, "AC", "presidente", 22, 13, "municipio")


def test_bad_rows_and_an_unknown_level_are_rejected() -> None:
    reader = PostgresBoletimReader(lambda: _Connection([("AC",)]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.totals(2026, 1, "AC", "presidente")
    reader = PostgresBoletimReader(lambda: _Connection([("nominal", True, 22, 1)]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.totals(2026, 1, "AC", "presidente")
    reader = PostgresBoletimReader(lambda: _Connection([("nominal", "partido", 22, 1)]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.totals(2026, 1, "AC", "presidente")
    reader = PostgresBoletimReader(lambda: _Connection([(1, None, 1)]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.municipalities(2026, 1, "AC", "presidente", 22)
    connection = _Connection([])
    reader = PostgresBoletimReader(lambda: connection)
    with pytest.raises(InvalidNivelError):
        reader.comparison(2026, 1, "AC", "presidente", 22, 13, "bairro")
    assert connection.statements == []


def test_party_power_derives_the_party_and_keeps_the_two_vote_sums() -> None:
    connection = _Connection([(1120, 15, 10, 4, 80)])
    reader = PostgresBoletimReader(lambda: connection)
    found = reader.party_power(2026, 1, ("AC",), "deputadoFederal", "municipio")
    sql, params = connection.statements[0]
    assert params == (
        2026,
        1,
        ["AC"],
        "deputadoFederal",
        2026,
        1,
        ["AC"],
        "deputadoFederal",
    )
    assert "uf = ANY(%s)" in sql
    assert "uf = %s" not in sql
    assert re.search(r"numero / 1000\b", sql)
    assert re.search(r"numero / 100\b", sql)
    assert re.search(r"numero / 10\b", sql)
    assert "'nominal'" in sql
    assert "'legenda'" in sql
    assert "tipo_voto" in sql
    assert "MAX(comparecimento_cargo)" in sql
    assert "SUM(quantidade)" in sql
    assert "SUM(comparecimento_cargo)" not in sql
    assert "COALESCE" in sql
    assert "2026" not in sql
    assert "deputadoFederal" not in sql
    assert "'branco'" not in sql
    assert "'nulo'" not in sql
    row = found[0]
    assert row.municipio == 1120
    assert row.zona is None
    assert row.partido == 15
    assert row.votos_nominais == 10
    assert row.votos_legenda == 4
    assert row.comparecimento == 80
    assert row.votos == 14

    zoned = _Connection([(1120, 8, Decimal("22"), Decimal("7"), Decimal("0"), Decimal("19"))])
    zone = PostgresBoletimReader(lambda: zoned).party_power(2026, 1, ("AC",), "senador", "zona")[0]
    assert zone.zona == 8
    assert zone.partido == 22
    assert zone.votos_nominais == 7
    assert zone.votos_legenda == 0
    assert zone.comparecimento == 19
    assert isinstance(zone.votos_nominais, int)

    missing_zone = _Connection([(1120, None, 22, 1, 0, 5)])
    with pytest.raises(InvalidBoletimConsultaError):
        PostgresBoletimReader(lambda: missing_zone).party_power(2026, 1, ("AC",), "senador", "zona")

    untouched = _Connection([])
    with pytest.raises(InvalidNivelError):
        PostgresBoletimReader(lambda: untouched).party_power(
            2026, 1, ("AC",), "presidente", "secao"
        )
    assert untouched.statements == []


def test_party_power_aggregate_has_no_place_and_maps_decimals() -> None:
    norte = ("AC", "AP", "AM", "PA", "RO", "RR", "TO")
    sqls: list[str] = []
    for nivel in ("uf", "regiao", "pais"):
        connection = _Connection([(11, 89075, 3153, 487971)])
        found = PostgresBoletimReader(lambda connection=connection: connection).party_power(
            2026, 1, norte, "deputadoFederal", nivel
        )
        sql, params = connection.statements[0]
        sqls.append(sql)
        assert params[2] == list(norte)
        assert params[6] == list(norte)
        row = found[0]
        assert row.partido == 11
        assert row.votos_nominais == 89075
        assert row.votos_legenda == 3153
        assert row.votos == 92228
        assert row.comparecimento == 487971
        assert row.municipio is None
        assert row.zona is None
        assert row.regiao is None
    assert sqls[0] == sqls[1] == sqls[2]
    sql = sqls[0]
    outer = sql.rsplit("SELECT", 1)[1]
    assert "uf = ANY(%s)" in sql
    assert "MAX(comparecimento_cargo)" in sql
    assert "SUM(comparecimento_cargo)" not in sql
    assert re.search(r"numero / 1000\b", sql)
    assert re.search(r"numero / 100\b", sql)
    assert re.search(r"numero / 10\b", sql)
    assert "municipio" not in outer
    assert "zona" not in outer
    assert "secao" not in outer
    assert "CROSS JOIN presenca" in sql
    assert "GROUP BY ," not in sql
    assert "SELECT ," not in sql
    assert re.search(r"GROUP BY\s*\n\s*\)", sql) is None
    assert "Norte" not in sql
    assert "regiao" not in sql
    assert "pais" not in sql

    decimaled = _Connection([(Decimal("11"), Decimal("89075"), Decimal("3153"), Decimal("487971"))])
    decimal_row = PostgresBoletimReader(lambda: decimaled).party_power(
        2026, 1, ("AC",), "presidente", "uf"
    )[0]
    assert decimal_row.partido == 11
    assert decimal_row.votos == 92228
    assert isinstance(decimal_row.partido, int)
    assert isinstance(decimal_row.comparecimento, int)


def test_participation_maxes_each_section_before_adding() -> None:
    connection = _Connection([(1120, Decimal("613742"), Decimal("610115"))])
    reader = PostgresBoletimReader(lambda: connection)
    found = reader.participation(2026, 1, "AC", "presidente", "municipio")
    sql, params = connection.statements[0]
    assert params == (2026, 1, "AC", "presidente")
    assert "MAX(eleitores_aptos)" in sql
    assert "MAX(qtd_comparecimento)" in sql
    assert "SUM(eleitores_aptos)" not in sql
    assert "SUM(qtd_comparecimento)" not in sql
    assert "SUM(comparecimento_cargo)" not in sql
    assert "comparecimento_cargo" not in sql
    assert "eleitores_computados" not in sql
    assert "2026" not in sql
    assert "presidente" not in sql
    row = found[0]
    assert row.zona is None
    assert row.eleitores_aptos == 613742
    assert row.comparecimento == 610115
    assert isinstance(row.eleitores_aptos, int)
    assert isinstance(row.comparecimento, int)
    assert row.abstencao == 3627

    zoned = _Connection([(1120, 8, 100, 90)])
    zone = PostgresBoletimReader(lambda: zoned).participation(2026, 1, "AC", "senador", "zona")[0]
    assert zone.zona == 8
    assert zone.abstencao == 10
    assert "SUM(aptos)" in zoned.statements[0][0]
    assert "GROUP BY municipio, zona\n" in zoned.statements[0][0]

    untouched = _Connection([])
    with pytest.raises(InvalidNivelError):
        PostgresBoletimReader(lambda: untouched).participation(2026, 1, "AC", "presidente", "secao")
    assert untouched.statements == []


def test_blank_and_null_keeps_places_without_those_votes() -> None:
    connection = _Connection([(1120, Decimal("0"), Decimal("0"), Decimal("40"))])
    reader = PostgresBoletimReader(lambda: connection)
    found = reader.blank_and_null(2026, 1, "AC", "presidente", "municipio")
    sql, params = connection.statements[0]
    assert params == (2026, 1, "AC", "presidente", 2026, 1, "AC", "presidente")
    assert "MAX(comparecimento_cargo)" in sql
    assert "SUM(comparecimento_cargo)" not in sql
    assert "SUM(eleitores_aptos)" not in sql
    assert "SUM(qtd_comparecimento)" not in sql
    assert "SUM(quantidade)" in sql
    assert "tipo_voto = 'branco'" in sql
    assert "tipo_voto = 'nulo'" in sql
    assert "LEFT JOIN" in sql
    assert "'nominal'" not in sql
    assert "'legenda'" not in sql
    assert "2026" not in sql
    assert "presidente" not in sql
    row = found[0]
    assert row.zona is None
    assert row.branco == 0
    assert row.nulo == 0
    assert row.comparecimento == 40
    assert isinstance(row.branco, int)
    assert isinstance(row.nulo, int)
    assert row.votos == 0

    zoned = _Connection([(1120, 8, Decimal("2"), Decimal("3"), Decimal("19"))])
    zone = PostgresBoletimReader(lambda: zoned).blank_and_null(2026, 1, "AC", "senador", "zona")[0]
    assert (zone.zona, zone.branco, zone.nulo, zone.votos, zone.comparecimento) == (8, 2, 3, 5, 19)
    assert isinstance(zone.branco, int)

    untouched = _Connection([])
    with pytest.raises(InvalidNivelError):
        PostgresBoletimReader(lambda: untouched).blank_and_null(
            2026, 1, "AC", "presidente", "secao"
        )
    assert untouched.statements == []


def test_leading_candidate_ranks_nominal_numbers_and_maps_decimals() -> None:
    connection = _Connection(
        [(1120, 15123, Decimal("15"), Decimal("40"), None, None, None, Decimal("80"))]
    )
    reader = PostgresBoletimReader(lambda: connection)
    found = reader.leading_candidate(2026, 1, "AC", "deputadoEstadual", "municipio")
    sql, params = connection.statements[0]
    assert params == (
        2026,
        1,
        "AC",
        "deputadoEstadual",
        2026,
        1,
        "AC",
        "deputadoEstadual",
    )
    assert "MAX(comparecimento_cargo)" in sql
    assert "SUM(comparecimento_cargo)" not in sql
    assert "SUM(eleitores_aptos)" not in sql
    assert "SUM(qtd_comparecimento)" not in sql
    assert "SUM(quantidade)" in sql
    assert re.search(r"numero / 1000\b", sql)
    assert re.search(r"numero / 100\b", sql)
    assert re.search(r"numero / 10\b", sql)
    assert "ROW_NUMBER()" in sql
    assert "ORDER BY votos DESC, numero ASC" in sql
    assert "tipo_voto = 'nominal'" in sql
    assert "'legenda'" not in sql
    assert "LEFT JOIN" in sql
    assert "2026" not in sql
    assert "deputadoEstadual" not in sql
    row = found[0]
    assert row.zona is None
    assert (row.numero, row.partido, row.votos) == (15123, 15, 40)
    assert row.segundo_numero is None
    assert row.segundo_partido is None
    assert row.segundo_votos is None
    assert row.comparecimento == 80
    assert isinstance(row.votos, int)
    assert isinstance(row.partido, int)
    assert isinstance(row.comparecimento, int)

    zoned = _Connection([(1120, 3, 13012, 13, 9, 15111, 15, 4, 20)])
    zone = PostgresBoletimReader(lambda: zoned).leading_candidate(
        2026, 1, "AC", "deputadoFederal", "zona"
    )[0]
    assert zone.zona == 3
    assert (zone.numero, zone.partido, zone.votos) == (13012, 13, 9)
    assert (zone.segundo_numero, zone.segundo_partido, zone.segundo_votos) == (15111, 15, 4)

    untouched = _Connection([])
    with pytest.raises(InvalidNivelError):
        PostgresBoletimReader(lambda: untouched).leading_candidate(
            2026, 1, "AC", "presidente", "bairro"
        )
    assert untouched.statements == []


def test_present_ufs_binds_the_three_filters_and_normalizes_codes() -> None:
    connection = _Connection([("sp",), ("AC",)])
    reader = PostgresBoletimReader(lambda: connection)
    assert reader.present_ufs(2026, 1, "presidente") == ("SP", "AC")
    sql, params = connection.statements[0]
    expected = (
        "SELECT DISTINCT uf FROM raw.boletim "
        "WHERE ano = %s AND turno = %s AND cargo = %s ORDER BY uf"
    )
    assert sql == expected
    assert params == (2026, 1, "presidente")
    assert "presidente" not in sql
    assert "2026" not in sql

    reader = PostgresBoletimReader(lambda: _Connection([("AC", "extra")]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.present_ufs(2026, 1, "presidente")
    reader = PostgresBoletimReader(lambda: _Connection([(1,)]))
    with pytest.raises(InvalidBoletimConsultaError):
        reader.present_ufs(2026, 1, "presidente")


def test_connection_is_reused_and_closed_once() -> None:
    connection = _Connection([])
    calls = {"opened": 0}

    def connect() -> _Connection:
        calls["opened"] += 1
        return connection

    reader = PostgresBoletimReader(connect)
    reader.close()
    reader.totals(2026, 1, "AC", "presidente")
    reader.totals(2026, 1, "AC", "presidente")
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
