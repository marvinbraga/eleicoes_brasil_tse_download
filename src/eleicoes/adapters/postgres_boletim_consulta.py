"""Reads boletim aggregates from Postgres.

Repeated section figures are collapsed with MAX before they are added up.
``quantidade`` is the only column summed from ``raw.boletim``.
User values are bound, never interpolated.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Final

from eleicoes.adapters.postgres_sink import ConnectionFactory, SqlConnection
from eleicoes.domain.boletim_consulta import (
    BlankNullProjection,
    BrancosNulos,
    Comparativo,
    LinhaVoto,
    NominalProjection,
    Participacao,
    PoderPartido,
    PrimeiroColocado,
    SectionProjection,
    TotalCargo,
    VotosMunicipio,
    VotosZona,
)
from eleicoes.domain.errors import InvalidBoletimConsultaError, InvalidNivelError
from eleicoes.domain.values import Uf

_TOTAL_WIDTH: Final = 4
_MUNICIPIO_WIDTH: Final = 3
_ZONA_WIDTH: Final = 3
_LINE_WIDTH: Final = 6
_SECTION_WIDTH: Final = 5
_NOMINAL_WIDTH: Final = 3
_BLANK_WIDTH: Final = 2
_VOTE_COLUMNS: Final = 3
_POWER_VALUES: Final = 4
_TURNOUT_VALUES: Final = 2
_BLANK_NULL_VALUES: Final = 3
_LEADER_VALUES: Final = 7

_PLACE_COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    "municipio": ("municipio",),
    "zona": ("municipio", "zona"),
    "secao": ("municipio", "zona", "secao"),
}

_PRESENT_UFS: Final = (
    "SELECT DISTINCT uf FROM raw.boletim WHERE ano = %s AND turno = %s AND cargo = %s ORDER BY uf"
)

_TOTALS: Final = """
SELECT tipo_voto, partido, numero, SUM(quantidade) AS quantidade
FROM raw.boletim
WHERE ano = %s
  AND turno = %s
  AND uf = %s
  AND cargo = %s
GROUP BY tipo_voto, partido, numero
"""

_RANKING: Final = """
WITH secoes AS (
    SELECT
        municipio,
        zona,
        secao,
        MAX(comparecimento_cargo) AS comparecimento
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = %s
      AND cargo = %s
    GROUP BY municipio, zona, secao
),
presenca AS (
    SELECT municipio, SUM(comparecimento) AS comparecimento
    FROM secoes
    GROUP BY municipio
),
votos AS (
    SELECT municipio, SUM(quantidade) AS quantidade
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = %s
      AND cargo = %s
      AND tipo_voto = 'nominal'
      AND numero = %s
    GROUP BY municipio
)
SELECT
    presenca.municipio,
    COALESCE(votos.quantidade, 0) AS quantidade,
    presenca.comparecimento
FROM presenca
LEFT JOIN votos ON votos.municipio = presenca.municipio
"""

_ZONES: Final = """
WITH secoes AS (
    SELECT
        zona,
        secao,
        MAX(comparecimento_cargo) AS comparecimento
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = %s
      AND municipio = %s
      AND cargo = %s
    GROUP BY zona, secao
),
presenca AS (
    SELECT zona, SUM(comparecimento) AS comparecimento
    FROM secoes
    GROUP BY zona
),
votos AS (
    SELECT zona, SUM(quantidade) AS quantidade
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = %s
      AND municipio = %s
      AND cargo = %s
      AND tipo_voto = 'nominal'
      AND numero = %s
    GROUP BY zona
)
SELECT
    presenca.zona,
    COALESCE(votos.quantidade, 0) AS quantidade,
    presenca.comparecimento
FROM presenca
LEFT JOIN votos ON votos.zona = presenca.zona
"""

_LINES: Final = """
SELECT cargo, ordem_impressao, tipo_voto, partido, numero, quantidade
FROM raw.boletim
WHERE ano = %s
  AND turno = %s
  AND uf = %s
  AND municipio = %s
  AND zona = %s
  AND secao = %s
"""

_SECTIONS: Final = """
SELECT
    municipio,
    zona,
    secao,
    MAX(comparecimento_cargo) AS comparecimento,
    SUM(quantidade) AS quantidade
FROM raw.boletim
WHERE ano = %s
  AND turno = %s
  AND uf = %s
  AND cargo = %s
GROUP BY municipio, zona, secao
"""

_NOMINAL: Final = """
SELECT municipio, numero, SUM(quantidade) AS quantidade
FROM raw.boletim
WHERE ano = %s
  AND turno = %s
  AND uf = %s
  AND cargo = %s
  AND tipo_voto = 'nominal'
  AND numero IS NOT NULL
GROUP BY municipio, numero
"""

_BLANKS: Final = """
SELECT municipio, SUM(quantidade) AS quantidade
FROM raw.boletim
WHERE ano = %s
  AND turno = %s
  AND uf = %s
  AND cargo = %s
  AND tipo_voto IN ('branco', 'nulo')
GROUP BY municipio
"""


def _comparison_sql(columns: tuple[str, ...]) -> str:
    selected = ", ".join(columns)
    keys = ", ".join(f"presenca.{column}" for column in columns)
    join = " AND ".join(f"votos.{column} = presenca.{column}" for column in columns)
    return f"""
WITH secoes AS (
    SELECT
        municipio,
        zona,
        secao,
        MAX(comparecimento_cargo) AS comparecimento
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = %s
      AND cargo = %s
    GROUP BY municipio, zona, secao
),
presenca AS (
    SELECT {selected}, SUM(comparecimento) AS comparecimento
    FROM secoes
    GROUP BY {selected}
),
votos AS (
    SELECT {selected}, numero, SUM(quantidade) AS quantidade
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = %s
      AND cargo = %s
      AND tipo_voto = 'nominal'
      AND numero IN (%s, %s)
    GROUP BY {selected}, numero
)
SELECT
    {keys},
    COALESCE(MAX(votos.quantidade) FILTER (WHERE votos.numero = %s), 0),
    COALESCE(MAX(votos.quantidade) FILTER (WHERE votos.numero = %s), 0),
    presenca.comparecimento
FROM presenca
LEFT JOIN votos ON {join}
GROUP BY {keys}, presenca.comparecimento
"""


_COMPARISON: Final[dict[str, str]] = {
    level: _comparison_sql(columns) for level, columns in _PLACE_COLUMNS.items()
}

_CITY_OR_ZONE: Final[dict[str, tuple[str, ...]]] = {
    "municipio": ("municipio",),
    "zona": ("municipio", "zona"),
}

_PARTY_FROM_NUMBER: Final = """
CASE
    WHEN tipo_voto = 'legenda' THEN numero
    WHEN tipo_voto = 'nominal' AND numero >= 10000 THEN numero / 1000
    WHEN tipo_voto = 'nominal' AND numero >= 1000 THEN numero / 100
    WHEN tipo_voto = 'nominal' AND numero >= 100 THEN numero / 10
    WHEN tipo_voto = 'nominal' THEN numero
END
"""


def _column_prefix(columns: tuple[str, ...]) -> str:
    if not columns:
        return ""
    return f"{', '.join(columns)}, "


def _qualified_prefix(columns: tuple[str, ...]) -> str:
    if not columns:
        return ""
    joined = ", ".join(f"votos.{column}" for column in columns)
    return f"{joined},\n    "


def _group_clause(columns: tuple[str, ...]) -> str:
    if not columns:
        return ""
    return f"\n    GROUP BY {', '.join(columns)}"


def _vote_group(columns: tuple[str, ...]) -> str:
    if not columns:
        return "partido"
    return f"{', '.join(columns)}, partido"


def _party_join(columns: tuple[str, ...]) -> str:
    if not columns:
        return "CROSS JOIN presenca"
    matched = " AND ".join(f"votos.{column} = presenca.{column}" for column in columns)
    return f"JOIN presenca ON {matched}"


def _party_power_sql(columns: tuple[str, ...]) -> str:
    party = _PARTY_FROM_NUMBER.strip()
    place = _column_prefix(columns)
    keys = _qualified_prefix(columns)
    grouped = _group_clause(columns)
    vote_group = _vote_group(columns)
    joined = _party_join(columns)
    return f"""
WITH secoes AS (
    SELECT
        municipio,
        zona,
        secao,
        MAX(comparecimento_cargo) AS comparecimento
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = ANY(%s)
      AND cargo = %s
    GROUP BY municipio, zona, secao
),
presenca AS (
    SELECT {place}SUM(comparecimento) AS comparecimento
    FROM secoes{grouped}
),
linhas AS (
    SELECT
        {place}tipo_voto,
        quantidade,
        {party} AS partido
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = ANY(%s)
      AND cargo = %s
      AND tipo_voto IN ('nominal', 'legenda')
      AND numero BETWEEN 0 AND 99999
      AND (tipo_voto = 'nominal' OR numero BETWEEN 0 AND 99)
),
votos AS (
    SELECT
        {place}partido,
        COALESCE(SUM(quantidade) FILTER (WHERE tipo_voto = 'nominal'), 0) AS votos_nominais,
        COALESCE(SUM(quantidade) FILTER (WHERE tipo_voto = 'legenda'), 0) AS votos_legenda
    FROM linhas
    GROUP BY {vote_group}
)
SELECT
    {keys}votos.partido,
    votos.votos_nominais,
    votos.votos_legenda,
    presenca.comparecimento
FROM votos
{joined}
"""


_AGGREGATE_LEVELS: Final[frozenset[str]] = frozenset({"uf", "regiao", "pais"})


def _party_power_queries() -> dict[str, str]:
    queries = {level: _party_power_sql(columns) for level, columns in _CITY_OR_ZONE.items()}
    aggregate = _party_power_sql(())
    for level in _AGGREGATE_LEVELS:
        queries[level] = aggregate
    return queries


_PARTY_POWER: Final[dict[str, str]] = _party_power_queries()

_NOMINAL_PARTY: Final = """
CASE
    WHEN numero >= 10000 THEN numero / 1000
    WHEN numero >= 1000 THEN numero / 100
    WHEN numero >= 100 THEN numero / 10
    ELSE numero
END
"""


def _participation_sql(columns: tuple[str, ...]) -> str:
    selected = ", ".join(columns)
    return f"""
WITH secoes AS (
    SELECT
        municipio,
        zona,
        secao,
        MAX(eleitores_aptos) AS aptos,
        MAX(qtd_comparecimento) AS comparecimento
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = %s
      AND cargo = %s
    GROUP BY municipio, zona, secao
)
SELECT
    {selected},
    SUM(aptos) AS eleitores_aptos,
    SUM(comparecimento) AS comparecimento
FROM secoes
GROUP BY {selected}
"""


def _blank_null_sql(columns: tuple[str, ...]) -> str:
    selected = ", ".join(columns)
    keys = ", ".join(f"presenca.{column}" for column in columns)
    join = " AND ".join(f"votos.{column} = presenca.{column}" for column in columns)
    return f"""
WITH secoes AS (
    SELECT
        municipio,
        zona,
        secao,
        MAX(comparecimento_cargo) AS comparecimento
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = %s
      AND cargo = %s
    GROUP BY municipio, zona, secao
),
presenca AS (
    SELECT {selected}, SUM(comparecimento) AS comparecimento
    FROM secoes
    GROUP BY {selected}
),
votos AS (
    SELECT
        {selected},
        COALESCE(SUM(quantidade) FILTER (WHERE tipo_voto = 'branco'), 0) AS branco,
        COALESCE(SUM(quantidade) FILTER (WHERE tipo_voto = 'nulo'), 0) AS nulo
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = %s
      AND cargo = %s
      AND tipo_voto IN ('branco', 'nulo')
    GROUP BY {selected}
)
SELECT
    {keys},
    COALESCE(votos.branco, 0) AS branco,
    COALESCE(votos.nulo, 0) AS nulo,
    presenca.comparecimento
FROM presenca
LEFT JOIN votos ON {join}
"""


def _leading_sql(columns: tuple[str, ...]) -> str:
    selected = ", ".join(columns)
    keys = ", ".join(f"primeiro.{column}" for column in columns)
    presenca_join = " AND ".join(f"primeiro.{column} = presenca.{column}" for column in columns)
    segundo_join = " AND ".join(f"segundo.{column} = primeiro.{column}" for column in columns)
    party = _NOMINAL_PARTY.strip()
    return f"""
WITH secoes AS (
    SELECT
        municipio,
        zona,
        secao,
        MAX(comparecimento_cargo) AS comparecimento
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = %s
      AND cargo = %s
    GROUP BY municipio, zona, secao
),
presenca AS (
    SELECT {selected}, SUM(comparecimento) AS comparecimento
    FROM secoes
    GROUP BY {selected}
),
nominais AS (
    SELECT
        {selected},
        numero,
        SUM(quantidade) AS votos
    FROM raw.boletim
    WHERE ano = %s
      AND turno = %s
      AND uf = %s
      AND cargo = %s
      AND tipo_voto = 'nominal'
      AND numero BETWEEN 0 AND 99999
    GROUP BY {selected}, numero
),
ranked AS (
    SELECT
        {selected},
        numero,
        {party} AS partido,
        votos,
        ROW_NUMBER() OVER (
            PARTITION BY {selected}
            ORDER BY votos DESC, numero ASC
        ) AS posicao
    FROM nominais
)
SELECT
    {keys},
    primeiro.numero,
    primeiro.partido,
    primeiro.votos,
    segundo.numero,
    segundo.partido,
    segundo.votos,
    presenca.comparecimento
FROM ranked AS primeiro
JOIN presenca ON {presenca_join}
LEFT JOIN ranked AS segundo
    ON {segundo_join}
   AND segundo.posicao = 2
WHERE primeiro.posicao = 1
"""


_PARTICIPATION: Final[dict[str, str]] = {
    level: _participation_sql(columns) for level, columns in _CITY_OR_ZONE.items()
}
_BLANK_NULL: Final[dict[str, str]] = {
    level: _blank_null_sql(columns) for level, columns in _CITY_OR_ZONE.items()
}
_LEADING: Final[dict[str, str]] = {
    level: _leading_sql(columns) for level, columns in _CITY_OR_ZONE.items()
}


class PostgresBoletimReader:
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect
        self._connection: SqlConnection | None = None

    def totals(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[TotalCargo, ...]:
        rows = self._rows(_TOTALS, (ano, turno, uf, cargo))
        return tuple(_total(row) for row in rows)

    def municipalities(
        self, ano: int, turno: int, uf: str, cargo: str, numero: int
    ) -> tuple[VotosMunicipio, ...]:
        params = (ano, turno, uf, cargo, ano, turno, uf, cargo, numero)
        return tuple(_municipio(row) for row in self._rows(_RANKING, params))

    def comparison(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        primeiro: int,
        segundo: int,
        nivel: str,
    ) -> tuple[Comparativo, ...]:
        sql = _COMPARISON.get(nivel)
        if sql is None:
            raise InvalidNivelError(nivel)
        params = (
            ano,
            turno,
            uf,
            cargo,
            ano,
            turno,
            uf,
            cargo,
            primeiro,
            segundo,
            primeiro,
            segundo,
        )
        return tuple(_comparativo(row, nivel) for row in self._rows(sql, params))

    def party_power(
        self, ano: int, turno: int, ufs: tuple[str, ...], cargo: str, nivel: str
    ) -> tuple[PoderPartido, ...]:
        sql = _PARTY_POWER.get(nivel)
        if sql is None:
            raise InvalidNivelError(nivel)
        states = list(ufs)
        params = (ano, turno, states, cargo, ano, turno, states, cargo)
        return tuple(_poder(row, nivel) for row in self._rows(sql, params))

    def participation(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[Participacao, ...]:
        sql = _PARTICIPATION.get(nivel)
        if sql is None:
            raise InvalidNivelError(nivel)
        params = (ano, turno, uf, cargo)
        return tuple(_participacao(row, nivel) for row in self._rows(sql, params))

    def blank_and_null(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[BrancosNulos, ...]:
        sql = _BLANK_NULL.get(nivel)
        if sql is None:
            raise InvalidNivelError(nivel)
        params = (ano, turno, uf, cargo, ano, turno, uf, cargo)
        return tuple(_brancos(row, nivel) for row in self._rows(sql, params))

    def leading_candidate(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[PrimeiroColocado, ...]:
        sql = _LEADING.get(nivel)
        if sql is None:
            raise InvalidNivelError(nivel)
        params = (ano, turno, uf, cargo, ano, turno, uf, cargo)
        return tuple(_primeiro(row, nivel) for row in self._rows(sql, params))

    def section_lines(
        self, ano: int, turno: int, uf: str, municipio: int, zona: int, secao: int
    ) -> tuple[LinhaVoto, ...]:
        params = (ano, turno, uf, municipio, zona, secao)
        return tuple(_linha(row) for row in self._rows(_LINES, params))

    def zones(
        self, ano: int, turno: int, uf: str, municipio: int, cargo: str, numero: int
    ) -> tuple[VotosZona, ...]:
        params = (ano, turno, uf, municipio, cargo, ano, turno, uf, municipio, cargo, numero)
        return tuple(_zona(row) for row in self._rows(_ZONES, params))

    def section_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[SectionProjection, ...]:
        rows = self._rows(_SECTIONS, (ano, turno, uf, cargo))
        return tuple(_section(row) for row in rows)

    def nominal_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[NominalProjection, ...]:
        rows = self._rows(_NOMINAL, (ano, turno, uf, cargo))
        return tuple(_nominal(row) for row in rows)

    def blank_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[BlankNullProjection, ...]:
        rows = self._rows(_BLANKS, (ano, turno, uf, cargo))
        return tuple(_blank(row) for row in rows)

    def present_ufs(self, ano: int, turno: int, cargo: str) -> tuple[str, ...]:
        rows = self._rows(_PRESENT_UFS, (ano, turno, cargo))
        return tuple(_uf_code(row) for row in rows)

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


def _uf_code(row: Sequence[object]) -> str:
    _require_width(row, 1)
    return Uf(_text(row[0])).code


def _total(row: Sequence[object]) -> TotalCargo:
    _require_width(row, _TOTAL_WIDTH)
    return TotalCargo(
        tipo_voto=_text(row[0]),
        partido=_optional_integer(row[1]),
        numero=_optional_integer(row[2]),
        quantidade=_integer(row[3]),
    )


def _municipio(row: Sequence[object]) -> VotosMunicipio:
    _require_width(row, _MUNICIPIO_WIDTH)
    return VotosMunicipio(
        municipio=_integer(row[0]),
        quantidade=_integer(row[1]),
        comparecimento=_integer(row[2]),
    )


def _comparativo(row: Sequence[object], nivel: str) -> Comparativo:
    columns = _PLACE_COLUMNS[nivel]
    _require_width(row, len(columns) + _VOTE_COLUMNS)
    zona = _integer(row[1]) if len(columns) > 1 else None
    secao = _integer(row[2]) if len(columns) > 2 else None
    offset = len(columns)
    return Comparativo(
        municipio=_integer(row[0]),
        zona=zona,
        secao=secao,
        votos_primeiro=_integer(row[offset]),
        votos_segundo=_integer(row[offset + 1]),
        comparecimento=_integer(row[offset + 2]),
    )


def _poder(row: Sequence[object], nivel: str) -> PoderPartido:
    if nivel in _AGGREGATE_LEVELS:
        return _poder_sem_lugar(row)
    return _poder_no_lugar(row, nivel)


def _poder_sem_lugar(row: Sequence[object]) -> PoderPartido:
    _require_width(row, _POWER_VALUES)
    return PoderPartido(
        municipio=None,
        zona=None,
        partido=_integer(row[0]),
        votos_nominais=_integer(row[1]),
        votos_legenda=_integer(row[2]),
        comparecimento=_integer(row[3]),
    )


def _poder_no_lugar(row: Sequence[object], nivel: str) -> PoderPartido:
    columns = _CITY_OR_ZONE[nivel]
    _require_width(row, len(columns) + _POWER_VALUES)
    zona = _integer(row[1]) if len(columns) > 1 else None
    offset = len(columns)
    return PoderPartido(
        municipio=_integer(row[0]),
        zona=zona,
        partido=_integer(row[offset]),
        votos_nominais=_integer(row[offset + 1]),
        votos_legenda=_integer(row[offset + 2]),
        comparecimento=_integer(row[offset + 3]),
    )


def _participacao(row: Sequence[object], nivel: str) -> Participacao:
    columns = _CITY_OR_ZONE[nivel]
    _require_width(row, len(columns) + _TURNOUT_VALUES)
    zona = _integer(row[1]) if len(columns) > 1 else None
    offset = len(columns)
    return Participacao(
        municipio=_integer(row[0]),
        zona=zona,
        eleitores_aptos=_integer(row[offset]),
        comparecimento=_integer(row[offset + 1]),
    )


def _brancos(row: Sequence[object], nivel: str) -> BrancosNulos:
    columns = _CITY_OR_ZONE[nivel]
    _require_width(row, len(columns) + _BLANK_NULL_VALUES)
    zona = _integer(row[1]) if len(columns) > 1 else None
    offset = len(columns)
    return BrancosNulos(
        municipio=_integer(row[0]),
        zona=zona,
        branco=_integer(row[offset]),
        nulo=_integer(row[offset + 1]),
        comparecimento=_integer(row[offset + 2]),
    )


def _primeiro(row: Sequence[object], nivel: str) -> PrimeiroColocado:
    columns = _CITY_OR_ZONE[nivel]
    _require_width(row, len(columns) + _LEADER_VALUES)
    zona = _integer(row[1]) if len(columns) > 1 else None
    offset = len(columns)
    return PrimeiroColocado(
        municipio=_integer(row[0]),
        zona=zona,
        numero=_integer(row[offset]),
        partido=_integer(row[offset + 1]),
        votos=_integer(row[offset + 2]),
        segundo_numero=_optional_integer(row[offset + 3]),
        segundo_partido=_optional_integer(row[offset + 4]),
        segundo_votos=_optional_integer(row[offset + 5]),
        comparecimento=_integer(row[offset + 6]),
    )


def _linha(row: Sequence[object]) -> LinhaVoto:
    _require_width(row, _LINE_WIDTH)
    return LinhaVoto(
        cargo=_text(row[0]),
        ordem_impressao=_integer(row[1]),
        tipo_voto=_text(row[2]),
        partido=_optional_integer(row[3]),
        numero=_optional_integer(row[4]),
        quantidade=_integer(row[5]),
    )


def _zona(row: Sequence[object]) -> VotosZona:
    _require_width(row, _ZONA_WIDTH)
    return VotosZona(
        zona=_integer(row[0]),
        quantidade=_integer(row[1]),
        comparecimento=_integer(row[2]),
    )


def _section(row: Sequence[object]) -> SectionProjection:
    _require_width(row, _SECTION_WIDTH)
    return SectionProjection(
        municipio=_integer(row[0]),
        zona=_integer(row[1]),
        secao=_integer(row[2]),
        comparecimento=_integer(row[3]),
        quantidade=_integer(row[4]),
    )


def _nominal(row: Sequence[object]) -> NominalProjection:
    _require_width(row, _NOMINAL_WIDTH)
    return NominalProjection(
        municipio=_integer(row[0]),
        numero=_integer(row[1]),
        quantidade=_integer(row[2]),
    )


def _blank(row: Sequence[object]) -> BlankNullProjection:
    _require_width(row, _BLANK_WIDTH)
    return BlankNullProjection(municipio=_integer(row[0]), quantidade=_integer(row[1]))


def _require_width(row: Sequence[object], width: int) -> None:
    if len(row) != width:
        raise InvalidBoletimConsultaError(len(row))


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    raise InvalidBoletimConsultaError(value)


def _integer(value: object) -> int:
    if isinstance(value, str):
        return _parsed_int(value)
    if isinstance(value, bool):
        raise InvalidBoletimConsultaError(value)
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return _decimal_int(value)
    raise InvalidBoletimConsultaError(value)


def _decimal_int(value: Decimal) -> int:
    if not value.is_finite():
        raise InvalidBoletimConsultaError(value)
    whole = value.to_integral_value()
    if value != whole:
        raise InvalidBoletimConsultaError(value)
    return int(whole)


def _parsed_int(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise InvalidBoletimConsultaError(value) from exc


def _optional_integer(value: object) -> int | None:
    if value is None:
        return None
    return _integer(value)
