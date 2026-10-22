"""Lê analise.municipal_* numa transação só. Parâmetros sempre ligados; filtro de UF opcional."""

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Final

from eleicoes.adapters.async_query import query_cursor
from eleicoes.domain.errors import StoredReadError
from eleicoes.domain.forca_municipal import (
    MunicipalCountsByUf,
    MunicipalTotals,
    PartyCouncil,
    PartyMayors,
    StoredCouncil,
    StoredMayor,
    StoredMunicipality,
    StoredMunicipalResults,
    UfPartyCount,
    UfTotals,
)
from eleicoes.ports.async_sql import AsyncSqlConnection, AsyncSqlCursor

Row = Sequence[object]

CARGA_SQL: Final = (
    "SELECT to_timestamp(geracao, 'DDMMYYYYHH24MI')::timestamp, gerado_em "
    "FROM analise.municipal_carga WHERE ano = %s"
)
TOTAIS_SQL: Final = (
    "SELECT count(*), count(*) FILTER (WHERE nr_partido IS NOT NULL), "
    "count(*) FILTER (WHERE nr_partido IS NULL), count(*) FILTER (WHERE suplementar), "
    "COALESCE(sum(eleitorado), 0), COALESCE(sum(vagas_vereador), 0) "
    "FROM analise.municipal_prefeito WHERE ano = %s AND (%s::text IS NULL OR sg_uf = %s)"
)
VEREADORES_TOTAIS_SQL: Final = (
    "SELECT COALESCE(sum(v.eleitos), 0), "
    "count(*) FILTER (WHERE COALESCE(v.eleitos, 0) <> p.vagas_vereador) "
    "FROM analise.municipal_prefeito AS p "
    "LEFT JOIN (SELECT sg_uf, cd_municipio_tse, sum(eleitos) AS eleitos "
    "FROM analise.municipal_vereador WHERE ano = %s GROUP BY sg_uf, cd_municipio_tse) AS v "
    "USING (sg_uf, cd_municipio_tse) "
    "WHERE p.ano = %s AND (%s::text IS NULL OR p.sg_uf = %s)"
)
PREFEITOS_SQL: Final = (
    "SELECT nr_partido, min(sg_partido), count(*), sum(eleitorado) "
    "FROM analise.municipal_prefeito "
    "WHERE ano = %s AND nr_partido IS NOT NULL AND (%s::text IS NULL OR sg_uf = %s) "
    "GROUP BY nr_partido"
)
VEREADORES_SQL: Final = (
    "SELECT nr_partido, min(sg_partido), sum(eleitos), count(*) "
    "FROM analise.municipal_vereador WHERE ano = %s AND (%s::text IS NULL OR sg_uf = %s) "
    "GROUP BY nr_partido"
)
MUNICIPIOS_SQL: Final = (
    "SELECT sg_uf, cd_municipio_tse, nm_municipio, eleitorado, nr_partido, sg_partido, "
    "nm_urna, nr_turno, suplementar, dt_eleicao FROM analise.municipal_prefeito "
    "WHERE ano = %s AND sg_uf = %s ORDER BY nm_municipio, cd_municipio_tse"
)
VEREADORES_MUNICIPIO_SQL: Final = (
    "SELECT cd_municipio_tse, nr_partido, sg_partido, eleitos FROM analise.municipal_vereador "
    "WHERE ano = %s AND sg_uf = %s ORDER BY cd_municipio_tse, eleitos DESC, nr_partido"
)

UF_PREFEITOS_SQL: Final = (
    "SELECT sg_uf, count(*), count(*) FILTER (WHERE nr_partido IS NOT NULL), "
    "COALESCE(sum(eleitorado), 0) FROM analise.municipal_prefeito WHERE ano = %s GROUP BY sg_uf"
)
UF_VEREADORES_SQL: Final = (
    "SELECT sg_uf, COALESCE(sum(eleitos), 0) FROM analise.municipal_vereador "
    "WHERE ano = %s GROUP BY sg_uf"
)
UF_PARTIDO_PREFEITOS_SQL: Final = (
    "SELECT sg_uf, nr_partido, min(sg_partido), count(*), sum(eleitorado) "
    "FROM analise.municipal_prefeito WHERE ano = %s AND nr_partido IS NOT NULL "
    "GROUP BY sg_uf, nr_partido"
)
UF_PARTIDO_VEREADORES_SQL: Final = (
    "SELECT sg_uf, nr_partido, min(sg_partido), sum(eleitos) FROM analise.municipal_vereador "
    "WHERE ano = %s GROUP BY sg_uf, nr_partido"
)


class AsyncPostgresMunicipalReader:
    def __init__(self, connection: AsyncSqlConnection) -> None:
        self._connection = connection

    async def load(self, ano: int, uf: str | None) -> StoredMunicipalResults | None:
        async with query_cursor(self._connection) as cursor:
            carga = await _rows(cursor, CARGA_SQL, (ano,))
            if not carga:
                return None
            scope = (ano, uf, uf)
            totais = await _rows(cursor, TOTAIS_SQL, scope)
            vereadores_totais = await _rows(cursor, VEREADORES_TOTAIS_SQL, (ano, *scope))
            prefeitos = await _rows(cursor, PREFEITOS_SQL, scope)
            vereadores = await _rows(cursor, VEREADORES_SQL, scope)
            municipios: tuple[StoredMunicipality, ...] = ()
            if uf is not None:
                lugares = await _rows(cursor, MUNICIPIOS_SQL, (ano, uf))
                bancadas = await _rows(cursor, VEREADORES_MUNICIPIO_SQL, (ano, uf))
                municipios = _municipalities(lugares, bancadas)
        corte, importado_em = _carga(carga[0])
        return StoredMunicipalResults(
            ano=ano,
            corte=corte,
            importado_em=importado_em,
            totais=_totals(_single(totais), _single(vereadores_totais)),
            prefeitos=tuple(_mayors(row) for row in prefeitos),
            vereadores=tuple(_council(row) for row in vereadores),
            municipios=municipios,
        )

    async def party_counts_by_uf(self, ano: int) -> MunicipalCountsByUf | None:
        async with query_cursor(self._connection) as cursor:
            carga = await _rows(cursor, CARGA_SQL, (ano,))
            if not carga:
                return None
            prefeitos_uf = await _rows(cursor, UF_PREFEITOS_SQL, (ano,))
            vereadores_uf = await _rows(cursor, UF_VEREADORES_SQL, (ano,))
            prefeitos = await _rows(cursor, UF_PARTIDO_PREFEITOS_SQL, (ano,))
            vereadores = await _rows(cursor, UF_PARTIDO_VEREADORES_SQL, (ano,))
        corte, importado_em = _carga(carga[0])
        return MunicipalCountsByUf(
            corte=corte,
            importado_em=importado_em,
            totais=_uf_totals(prefeitos_uf, vereadores_uf),
            linhas=_uf_party_counts(prefeitos, vereadores),
        )


def _uf_totals(prefeitos: tuple[Row, ...], vereadores: tuple[Row, ...]) -> tuple[UfTotals, ...]:
    seats: dict[str, int] = {}
    for row in vereadores:
        uf, eleitos = _width(row, 2)
        seats[_text(uf)] = _int(eleitos)
    totals: list[UfTotals] = []
    for row in prefeitos:
        uf, municipios, com_prefeito, eleitorado = _width(row, 4)
        code = _text(uf)
        totals.append(
            UfTotals(
                code, _int(municipios), _int(com_prefeito), _int(eleitorado), seats.get(code, 0)
            )
        )
    return tuple(sorted(totals, key=lambda item: item.uf))


def _uf_party_counts(
    prefeitos: tuple[Row, ...], vereadores: tuple[Row, ...]
) -> tuple[UfPartyCount, ...]:
    """Une por (UF, partido); partido só com vereadores fica com prefeitos e eleitorado 0."""
    mayors: dict[tuple[str, int], tuple[str, int, int]] = {}
    for row in prefeitos:
        uf, partido, sigla, quantos, eleitorado = _width(row, 5)
        mayors[(_text(uf), _int(partido))] = (_text(sigla), _int(quantos), _int(eleitorado))
    council: dict[tuple[str, int], tuple[str, int]] = {}
    for row in vereadores:
        uf, partido, sigla, eleitos = _width(row, 4)
        council[(_text(uf), _int(partido))] = (_text(sigla), _int(eleitos))
    keys = sorted({*mayors, *council})
    return tuple(_uf_party(key, mayors.get(key), council.get(key)) for key in keys)


def _uf_party(
    key: tuple[str, int],
    mayors: tuple[str, int, int] | None,
    council: tuple[str, int] | None,
) -> UfPartyCount:
    sigla, prefeitos, eleitorado = mayors if mayors is not None else ("", 0, 0)
    if mayors is None and council is not None:
        sigla = council[0]
    return UfPartyCount(
        uf=key[0],
        partido=key[1],
        sigla=sigla,
        prefeitos=prefeitos,
        eleitorado=eleitorado,
        vereadores=council[1] if council is not None else 0,
    )


async def _rows(cursor: AsyncSqlCursor, sql: str, params: Sequence[object]) -> tuple[Row, ...]:
    await cursor.execute(sql, params)
    return tuple(tuple(row) for row in await cursor.fetchall())


def _single(rows: tuple[Row, ...]) -> Row:
    if len(rows) != 1:
        raise StoredReadError()
    return rows[0]


def _carga(row: Row) -> tuple[datetime, datetime]:
    corte, importado_em = _width(row, 2)
    if not isinstance(corte, datetime) or not isinstance(importado_em, datetime):
        raise StoredReadError()
    return corte, importado_em


def _totals(prefeitos: Row, vereadores: Row) -> MunicipalTotals:
    municipios, com, sem, suplementares, eleitorado, vagas = _width(prefeitos, 6)
    eleitos, divergencias = _width(vereadores, 2)
    return MunicipalTotals(
        municipios=_int(municipios),
        com_prefeito=_int(com),
        sem_prefeito=_int(sem),
        suplementares=_int(suplementares),
        eleitorado=_int(eleitorado),
        vereadores=_int(eleitos),
        vagas_vereador=_int(vagas),
        divergencias_vagas=_int(divergencias),
    )


def _mayors(row: Row) -> PartyMayors:
    partido, sigla, prefeitos, eleitorado = _width(row, 4)
    return PartyMayors(_int(partido), _text(sigla), _int(prefeitos), _int(eleitorado))


def _council(row: Row) -> PartyCouncil:
    partido, sigla, vereadores, municipios = _width(row, 4)
    return PartyCouncil(_int(partido), _text(sigla), _int(vereadores), _int(municipios))


def _municipalities(
    lugares: tuple[Row, ...], bancadas: tuple[Row, ...]
) -> tuple[StoredMunicipality, ...]:
    by_place: dict[str, list[StoredCouncil]] = {}
    for row in bancadas:
        codigo, partido, sigla, eleitos = _width(row, 4)
        seats = StoredCouncil(_int(partido), _text(sigla), _int(eleitos))
        by_place.setdefault(_text(codigo), []).append(seats)
    return tuple(_municipality(row, by_place) for row in lugares)


def _municipality(row: Row, by_place: dict[str, list[StoredCouncil]]) -> StoredMunicipality:
    uf, codigo, nome, eleitorado, *prefeito = _width(row, 10)
    ue = _text(codigo)
    return StoredMunicipality(
        uf=_text(uf),
        ue=ue,
        nome=_text(nome),
        eleitorado=_int(eleitorado),
        prefeito=_mayor(prefeito),
        vereadores=tuple(by_place.get(ue, ())),
    )


def _mayor(values: Sequence[object]) -> StoredMayor | None:
    partido, sigla, nome_urna, turno, suplementar, data_eleicao = values
    if partido is None:
        return None
    if not isinstance(suplementar, bool) or not isinstance(data_eleicao, date):
        raise StoredReadError()
    return StoredMayor(
        partido=_int(partido),
        sigla=_text(sigla),
        nome_urna=_text(nome_urna),
        turno=_int(turno),
        suplementar=suplementar,
        data_eleicao=data_eleicao,
    )


def _width(row: Row, size: int) -> Sequence[object]:
    if len(row) != size:
        raise StoredReadError()
    return row


def _int(value: object) -> int:
    """count() volta int e sum() de bigint volta Decimal no psycopg."""
    if isinstance(value, bool):
        raise StoredReadError()
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal) and value == value.to_integral_value():
        return int(value)
    raise StoredReadError()


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise StoredReadError()
    return value
