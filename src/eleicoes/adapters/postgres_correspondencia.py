"""Reads correspondence from Postgres. User values are bound, never interpolated."""

from collections.abc import Sequence
from datetime import datetime
from typing import Final

from eleicoes.adapters.postgres_sink import ConnectionFactory, SqlConnection
from eleicoes.domain.correspondencia import (
    Contingencia,
    MudancaGeracao,
    ProjecaoContingencia,
    ProjecaoSecao,
    ResumoUf,
    Secao,
    StatusCorrespondencia,
)
from eleicoes.domain.correspondencia.tokens import is_blank_token
from eleicoes.domain.errors import InvalidCorrespondenceRecordError

_TIMESTAMP: Final = "to_timestamp(c.geracao, 'DDMMYYYYHH24MI')"
_SECTION_KEY: Final = "c.sg_uf, c.cd_municipio, c.nr_zona, c.nr_secao"
_CONTINGENCY_KEY: Final = "c.sg_uf, c.cd_municipio, c.nr_zona, c.nr_urna_esperada"
_TIMESTAMP_FORMATS: Final[tuple[str, ...]] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
)
_SECAO_WIDTH: Final = 18
_CONTINGENCIA_WIDTH: Final = 16
_RESUMO_WIDTH: Final = 9
_MUDANCA_WIDTH: Final = 17
_PROJECAO_SECAO_WIDTH: Final = 10
_PROJECAO_CONTINGENCIA_WIDTH: Final = 6

# Latest row only. `*` is the raw code; analise.secao.alterada drops it.
_LATEST_SECTIONS: Final = f"""
SELECT
    sg_uf,
    cd_municipio,
    nm_municipio,
    nr_zona,
    nr_secao,
    nr_local_votacao,
    nr_urna_esperada,
    cd_carga_urna_esperada,
    cd_flashcard_urna_esperada,
    dt_carga_urna_esperada,
    st_corresp_alterada,
    nm_maquina_geracao_midia,
    nr_sri_tpm_geracao_midia,
    nr_sri_instal_geracao_midia,
    nm_maquina_transm_corresp,
    nr_sri_tpm_transm_corresp,
    nr_sri_instal_transm_corresp,
    geracao_em
FROM (
    SELECT DISTINCT ON ({_SECTION_KEY})
        c.sg_uf,
        c.cd_municipio,
        c.nm_municipio,
        c.nr_zona,
        c.nr_secao,
        c.nr_local_votacao,
        c.nr_urna_esperada,
        c.cd_carga_urna_esperada,
        c.cd_flashcard_urna_esperada,
        c.dt_carga_urna_esperada,
        c.st_corresp_alterada,
        c.nm_maquina_geracao_midia,
        c.nr_sri_tpm_geracao_midia,
        c.nr_sri_instal_geracao_midia,
        c.nm_maquina_transm_corresp,
        c.nr_sri_tpm_transm_corresp,
        c.nr_sri_instal_transm_corresp,
        {_TIMESTAMP} AS geracao_em
    FROM raw.csec AS c
    WHERE (%s::text IS NULL OR c.sg_uf = %s)
    ORDER BY {_SECTION_KEY},
        {_TIMESTAMP} DESC
) AS latest
WHERE (%s::text IS NULL OR latest.st_corresp_alterada = %s)
"""

_LATEST_CONTINGENCIES: Final = f"""
SELECT
    sg_uf,
    cd_municipio,
    nm_municipio,
    nr_zona,
    nr_urna_esperada,
    cd_carga_urna_esperada,
    cd_flashcard_urna_esperada,
    dt_carga_urna_esperada,
    st_corresp_alterada,
    nm_maquina_geracao_midia,
    nr_sri_tpm_geracao_midia,
    nr_sri_instal_geracao_midia,
    nm_maquina_transm_corresp,
    nr_sri_tpm_transm_corresp,
    nr_sri_instal_transm_corresp,
    geracao_em
FROM (
    SELECT DISTINCT ON ({_CONTINGENCY_KEY})
        c.sg_uf,
        c.cd_municipio,
        c.nm_municipio,
        c.nr_zona,
        c.nr_urna_esperada,
        c.cd_carga_urna_esperada,
        c.cd_flashcard_urna_esperada,
        c.dt_carga_urna_esperada,
        c.st_corresp_alterada,
        c.nm_maquina_geracao_midia,
        c.nr_sri_tpm_geracao_midia,
        c.nr_sri_instal_geracao_midia,
        c.nm_maquina_transm_corresp,
        c.nr_sri_tpm_transm_corresp,
        c.nr_sri_instal_transm_corresp,
        {_TIMESTAMP} AS geracao_em
    FROM raw.ccont AS c
    WHERE (%s::text IS NULL OR c.sg_uf = %s)
    ORDER BY {_CONTINGENCY_KEY},
        {_TIMESTAMP} DESC
) AS latest
WHERE (%s::text IS NULL OR latest.st_corresp_alterada = %s)
"""

_GENERATIONS: Final = f"""
SELECT
    c.sg_uf,
    c.cd_municipio,
    c.nm_municipio,
    c.nr_zona,
    c.nr_secao,
    c.nr_local_votacao,
    c.nr_urna_esperada,
    c.cd_carga_urna_esperada,
    c.cd_flashcard_urna_esperada,
    c.dt_carga_urna_esperada,
    c.st_corresp_alterada,
    c.nm_maquina_geracao_midia,
    c.nr_sri_tpm_geracao_midia,
    c.nr_sri_instal_geracao_midia,
    c.nm_maquina_transm_corresp,
    c.nr_sri_tpm_transm_corresp,
    c.nr_sri_instal_transm_corresp,
    {_TIMESTAMP} AS geracao_em
FROM raw.csec AS c
WHERE c.sg_uf = %s
  AND (%s::integer IS NULL OR c.nr_zona::integer = %s)
  AND (%s::integer IS NULL OR c.nr_secao::integer = %s)
ORDER BY {_TIMESTAMP} ASC
"""

_CHANGES: Final = f"""
WITH ranked AS (
    SELECT
        c.sg_uf,
        c.cd_municipio,
        c.nm_municipio,
        c.nr_zona,
        c.nr_secao,
        c.nr_local_votacao,
        c.nr_urna_esperada,
        c.cd_carga_urna_esperada,
        c.cd_flashcard_urna_esperada,
        c.nm_maquina_geracao_midia,
        c.geracao,
        row_number() OVER (
            PARTITION BY {_SECTION_KEY}
            ORDER BY {_TIMESTAMP} DESC
        ) AS posicao
    FROM raw.csec AS c
    WHERE (%s::text IS NULL OR c.sg_uf = %s)
)
SELECT
    atual.sg_uf,
    atual.cd_municipio,
    atual.nm_municipio,
    atual.nr_zona,
    atual.nr_secao,
    to_timestamp(anterior.geracao, 'DDMMYYYYHH24MI'),
    to_timestamp(atual.geracao, 'DDMMYYYYHH24MI'),
    COALESCE(anterior.nr_urna_esperada, ''),
    COALESCE(atual.nr_urna_esperada, ''),
    COALESCE(anterior.cd_carga_urna_esperada, ''),
    COALESCE(atual.cd_carga_urna_esperada, ''),
    COALESCE(anterior.cd_flashcard_urna_esperada, ''),
    COALESCE(atual.cd_flashcard_urna_esperada, ''),
    COALESCE(anterior.nr_local_votacao, ''),
    COALESCE(atual.nr_local_votacao, ''),
    COALESCE(anterior.nm_maquina_geracao_midia, ''),
    COALESCE(atual.nm_maquina_geracao_midia, '')
FROM ranked AS atual
INNER JOIN ranked AS anterior
    ON atual.sg_uf = anterior.sg_uf
    AND atual.cd_municipio = anterior.cd_municipio
    AND atual.nr_zona = anterior.nr_zona
    AND atual.nr_secao = anterior.nr_secao
    AND atual.posicao = 1
    AND anterior.posicao = 2
WHERE COALESCE(atual.nr_urna_esperada, '')
        IS DISTINCT FROM COALESCE(anterior.nr_urna_esperada, '')
    OR COALESCE(atual.cd_carga_urna_esperada, '')
        IS DISTINCT FROM COALESCE(anterior.cd_carga_urna_esperada, '')
    OR COALESCE(atual.cd_flashcard_urna_esperada, '')
        IS DISTINCT FROM COALESCE(anterior.cd_flashcard_urna_esperada, '')
    OR COALESCE(atual.nr_local_votacao, '')
        IS DISTINCT FROM COALESCE(anterior.nr_local_votacao, '')
    OR COALESCE(atual.nm_maquina_geracao_midia, '')
        IS DISTINCT FROM COALESCE(anterior.nm_maquina_geracao_midia, '')
ORDER BY atual.sg_uf, atual.cd_municipio, atual.nr_zona, atual.nr_secao
"""

_SUMMARIES: Final = f"""
WITH secoes AS (
    SELECT DISTINCT ON ({_SECTION_KEY})
        c.sg_uf,
        c.cd_municipio,
        c.nr_zona,
        c.nr_local_votacao,
        c.st_corresp_alterada
    FROM raw.csec AS c
    ORDER BY {_SECTION_KEY},
        {_TIMESTAMP} DESC
),
contingencias AS (
    SELECT DISTINCT ON ({_CONTINGENCY_KEY})
        c.sg_uf,
        c.st_corresp_alterada
    FROM raw.ccont AS c
    ORDER BY {_CONTINGENCY_KEY},
        {_TIMESTAMP} DESC
),
resumo_secao AS (
    SELECT
        sg_uf,
        count(*) AS secoes,
        count(DISTINCT cd_municipio) AS municipios,
        count(DISTINCT (cd_municipio, nr_zona)) AS zonas,
        count(DISTINCT (cd_municipio, nr_local_votacao)) AS locais,
        count(*) FILTER (WHERE st_corresp_alterada = 'S') AS alteradas,
        count(*) FILTER (WHERE st_corresp_alterada = '*') AS novas
    FROM secoes
    GROUP BY sg_uf
),
resumo_contingencia AS (
    SELECT
        sg_uf,
        count(*) AS urnas_contingencia,
        count(*) FILTER (WHERE st_corresp_alterada = '*') AS contingencias_novas
    FROM contingencias
    GROUP BY sg_uf
)
SELECT
    COALESCE(s.sg_uf, c.sg_uf),
    COALESCE(s.secoes, 0),
    COALESCE(s.municipios, 0),
    COALESCE(s.zonas, 0),
    COALESCE(s.locais, 0),
    COALESCE(s.alteradas, 0),
    COALESCE(s.novas, 0),
    COALESCE(c.urnas_contingencia, 0),
    COALESCE(c.contingencias_novas, 0)
FROM resumo_secao AS s
FULL OUTER JOIN resumo_contingencia AS c ON c.sg_uf = s.sg_uf
ORDER BY 1
"""

_SECTION_PROJECTIONS: Final = f"""
SELECT
    sg_uf,
    cd_municipio,
    nm_municipio,
    nr_zona,
    nr_secao,
    nr_urna_esperada,
    cd_carga_urna_esperada,
    cd_flashcard_urna_esperada,
    st_corresp_alterada,
    nm_maquina_geracao_midia
FROM (
    SELECT DISTINCT ON ({_SECTION_KEY})
        c.sg_uf,
        c.cd_municipio,
        c.nm_municipio,
        c.nr_zona,
        c.nr_secao,
        c.nr_urna_esperada,
        c.cd_carga_urna_esperada,
        c.cd_flashcard_urna_esperada,
        c.st_corresp_alterada,
        c.nm_maquina_geracao_midia
    FROM raw.csec AS c
    WHERE (%s::text IS NULL OR c.sg_uf = %s)
    ORDER BY {_SECTION_KEY},
        {_TIMESTAMP} DESC
) AS latest
"""

_CONTINGENCY_PROJECTIONS: Final = f"""
SELECT
    sg_uf,
    cd_municipio,
    nm_municipio,
    nr_zona,
    nr_urna_esperada,
    st_corresp_alterada
FROM (
    SELECT DISTINCT ON ({_CONTINGENCY_KEY})
        c.sg_uf,
        c.cd_municipio,
        c.nm_municipio,
        c.nr_zona,
        c.nr_urna_esperada,
        c.st_corresp_alterada
    FROM raw.ccont AS c
    WHERE (%s::text IS NULL OR c.sg_uf = %s)
    ORDER BY {_CONTINGENCY_KEY},
        {_TIMESTAMP} DESC
) AS latest
"""


class PostgresCorrespondenciaReader:
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect
        self._connection: SqlConnection | None = None

    def secoes(self, uf: str | None, status: StatusCorrespondencia | None) -> tuple[Secao, ...]:
        params = (*_text_pair(uf), *_status_pair(status))
        return tuple(_secao(row) for row in self._rows(_LATEST_SECTIONS, params))

    def contingencias(
        self, uf: str | None, status: StatusCorrespondencia | None
    ) -> tuple[Contingencia, ...]:
        params = (*_text_pair(uf), *_status_pair(status))
        return tuple(_contingencia(row) for row in self._rows(_LATEST_CONTINGENCIES, params))

    def resumos(self) -> tuple[ResumoUf, ...]:
        return tuple(_resumo(row) for row in self._rows(_SUMMARIES, ()))

    def mudancas(self, uf: str | None) -> tuple[MudancaGeracao, ...]:
        return tuple(_mudanca(row) for row in self._rows(_CHANGES, _text_pair(uf)))

    def geracoes(self, uf: str, zona: int | None, secao: int | None) -> tuple[Secao, ...]:
        params: tuple[object, ...] = (uf, *_int_pair(zona), *_int_pair(secao))
        return tuple(_secao(row) for row in self._rows(_GENERATIONS, params))

    def projecoes(self, uf: str | None) -> tuple[ProjecaoSecao, ...]:
        rows = self._rows(_SECTION_PROJECTIONS, _text_pair(uf))
        return tuple(_projecao_secao(row) for row in rows)

    def projecoes_contingencia(self, uf: str | None) -> tuple[ProjecaoContingencia, ...]:
        rows = self._rows(_CONTINGENCY_PROJECTIONS, _text_pair(uf))
        return tuple(_projecao_contingencia(row) for row in rows)

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


def _text_pair(value: str | None) -> tuple[str | None, str | None]:
    return (value, value)


def _int_pair(value: int | None) -> tuple[int | None, int | None]:
    return (value, value)


def _status_pair(status: StatusCorrespondencia | None) -> tuple[str | None, str | None]:
    if status is None:
        return (None, None)
    return (status.value, status.value)


def _secao(row: Sequence[object]) -> Secao:
    _require_width(row, _SECAO_WIDTH)
    return Secao(
        uf=_text(row[0]),
        codigo_municipio=_text(row[1]),
        municipio=_text(row[2]),
        zona=_integer(row[3]),
        numero=_integer(row[4]),
        local_votacao=_text(row[5]),
        urna_esperada=_text(row[6]),
        codigo_carga=_text(row[7]),
        flashcard=_text(row[8]),
        carga_em=_optional_datetime(row[9]),
        status=StatusCorrespondencia.from_code(_text(row[10])),
        maquina_geracao=_text(row[11]),
        tpm_geracao=_text(row[12]),
        instalacao_geracao=_text(row[13]),
        maquina_transmissao=_text(row[14]),
        tpm_transmissao=_text(row[15]),
        instalacao_transmissao=_text(row[16]),
        geracao_em=_required_datetime(row[17]),
    )


def _contingencia(row: Sequence[object]) -> Contingencia:
    _require_width(row, _CONTINGENCIA_WIDTH)
    return Contingencia(
        uf=_text(row[0]),
        codigo_municipio=_text(row[1]),
        municipio=_text(row[2]),
        zona=_integer(row[3]),
        urna_esperada=_text(row[4]),
        codigo_carga=_text(row[5]),
        flashcard=_text(row[6]),
        carga_em=_optional_datetime(row[7]),
        status=StatusCorrespondencia.from_code(_text(row[8])),
        maquina_geracao=_text(row[9]),
        tpm_geracao=_text(row[10]),
        instalacao_geracao=_text(row[11]),
        maquina_transmissao=_text(row[12]),
        tpm_transmissao=_text(row[13]),
        instalacao_transmissao=_text(row[14]),
        geracao_em=_required_datetime(row[15]),
    )


def _resumo(row: Sequence[object]) -> ResumoUf:
    _require_width(row, _RESUMO_WIDTH)
    return ResumoUf(
        uf=_text(row[0]),
        secoes=_integer(row[1]),
        municipios=_integer(row[2]),
        zonas=_integer(row[3]),
        locais=_integer(row[4]),
        alteradas=_integer(row[5]),
        novas=_integer(row[6]),
        urnas_contingencia=_integer(row[7]),
        contingencias_novas=_integer(row[8]),
    )


def _mudanca(row: Sequence[object]) -> MudancaGeracao:
    _require_width(row, _MUDANCA_WIDTH)
    return MudancaGeracao(
        uf=_text(row[0]),
        codigo_municipio=_text(row[1]),
        municipio=_text(row[2]),
        zona=_integer(row[3]),
        secao=_integer(row[4]),
        geracao_anterior=_required_datetime(row[5]),
        geracao_atual=_required_datetime(row[6]),
        urna_anterior=_text(row[7]),
        urna_atual=_text(row[8]),
        carga_anterior=_text(row[9]),
        carga_atual=_text(row[10]),
        flashcard_anterior=_text(row[11]),
        flashcard_atual=_text(row[12]),
        local_anterior=_text(row[13]),
        local_atual=_text(row[14]),
        maquina_anterior=_text(row[15]),
        maquina_atual=_text(row[16]),
    )


def _projecao_secao(row: Sequence[object]) -> ProjecaoSecao:
    _require_width(row, _PROJECAO_SECAO_WIDTH)
    return ProjecaoSecao(
        uf=_text(row[0]),
        codigo_municipio=_text(row[1]),
        municipio=_text(row[2]),
        zona=_integer(row[3]),
        secao=_integer(row[4]),
        urna=_text(row[5]),
        carga=_text(row[6]),
        flashcard=_text(row[7]),
        status=StatusCorrespondencia.from_code(_text(row[8])),
        maquina_geracao=_text(row[9]),
    )


def _projecao_contingencia(row: Sequence[object]) -> ProjecaoContingencia:
    _require_width(row, _PROJECAO_CONTINGENCIA_WIDTH)
    return ProjecaoContingencia(
        uf=_text(row[0]),
        codigo_municipio=_text(row[1]),
        municipio=_text(row[2]),
        zona=_integer(row[3]),
        urna=_text(row[4]),
        status=StatusCorrespondencia.from_code(_text(row[5])),
    )


def _require_width(row: Sequence[object], width: int) -> None:
    if len(row) != width:
        raise InvalidCorrespondenceRecordError(len(row))


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    raise InvalidCorrespondenceRecordError(value)


def _integer(value: object) -> int:
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as exc:
            raise InvalidCorrespondenceRecordError(value) from exc
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise InvalidCorrespondenceRecordError(value)


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise InvalidCorrespondenceRecordError(value)
    return _parsed_timestamp(value)


def _parsed_timestamp(value: str) -> datetime | None:
    stripped = value.strip()
    if is_blank_token(stripped):
        return None
    for pattern in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(stripped, pattern)
        except ValueError:
            continue
    raise InvalidCorrespondenceRecordError(stripped)


def _required_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    raise InvalidCorrespondenceRecordError(value)
