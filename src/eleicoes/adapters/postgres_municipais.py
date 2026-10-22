"""Lê o raw municipal e grava analise.municipal_* numa transação. Valores sempre ligados."""

import csv
import io
from collections.abc import Sequence
from datetime import datetime
from typing import Final

from eleicoes.adapters.postgres_sink import ConnectionFactory, SqlConnection, SqlCursor
from eleicoes.domain.errors import InvalidMunicipalRowError
from eleicoes.domain.municipais import (
    CandidateRow,
    ElectorateRow,
    MunicipalBuild,
    MunicipalRaw,
    SeatRow,
    parse_int,
    parse_tse_date,
)

_CANDIDATOS: Final = (
    "SELECT sg_uf, sg_ue, nm_ue, cd_tipo_eleicao, dt_eleicao, nr_turno, cd_cargo, "
    "sq_candidato, nm_urna_candidato, nr_partido, sg_partido, cd_sit_tot_turno "
    "FROM raw.consulta_cand WHERE ano_eleicao = %s "
    "AND cd_cargo IN ('11', '13') AND cd_sit_tot_turno IN ('1', '2', '3')"
)
_ELEITORADO: Final = (
    "SELECT sg_uf, sg_ue, nm_ue, cd_tipo_eleicao, nr_turno, cd_cargo, qt_aptos "
    "FROM raw.detalhe_votacao_munzona WHERE ano_eleicao = %s AND cd_cargo = '11'"
)
_VAGAS: Final = (
    "SELECT sg_uf, sg_ue, cd_tipo_eleicao, cd_cargo, qt_vaga "
    "FROM raw.consulta_vagas WHERE ano_eleicao = %s AND cd_cargo = '13'"
)
_GERACAO: Final = (
    "SELECT min(to_timestamp(geracao, 'DDMMYYYYHH24MI')) FROM raw.consulta_cand "
    "WHERE ano_eleicao = %s"
)
_PREFEITO_COLUMNS: Final = (
    "ano, sg_uf, cd_municipio_tse, nm_municipio, eleitorado, vagas_vereador, nr_partido, "
    "sg_partido, nm_urna, sq_candidato, dt_eleicao, nr_turno, suplementar"
)
_VEREADOR_COLUMNS: Final = "ano, sg_uf, cd_municipio_tse, nr_partido, sg_partido, eleitos"


class PostgresMunicipalStore:
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect
        self._connection: SqlConnection | None = None

    def read_raw(self, year: int) -> MunicipalRaw:
        connection = self._open()
        with connection.transaction(), connection.cursor() as cursor:
            geracao = _generation(_fetch(cursor, _GERACAO, year))
            candidatos = tuple(_candidate(row) for row in _fetch(cursor, _CANDIDATOS, year))
            eleitorado = tuple(_electorate(row) for row in _fetch(cursor, _ELEITORADO, year))
            vagas = tuple(_seat(row) for row in _fetch(cursor, _VAGAS, year))
        return MunicipalRaw(geracao, candidatos, eleitorado, vagas)

    def save(self, year: int, built: MunicipalBuild) -> None:
        connection = self._open()
        with connection.transaction(), connection.cursor() as cursor:
            cursor.execute("DELETE FROM analise.municipal_carga WHERE ano = %s", (year,))
            cursor.execute(
                "INSERT INTO analise.municipal_carga "
                "(ano, geracao, municipios, prefeitos, vereadores, divergencias_vagas) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    year,
                    built.geracao,
                    len(built.municipios),
                    built.prefeitos,
                    built.vereadores_eleitos,
                    len(built.divergencias),
                ),
            )
            _copy(cursor, "analise.municipal_prefeito", _PREFEITO_COLUMNS, _mayor_rows(year, built))
            _copy(
                cursor, "analise.municipal_vereador", _VEREADOR_COLUMNS, _council_rows(year, built)
            )

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _open(self) -> SqlConnection:
        if self._connection is None:
            self._connection = self._connect()
        return self._connection


def _fetch(cursor: SqlCursor, sql: str, year: int) -> Sequence[Sequence[object]]:
    cursor.execute(sql, (str(year),))
    return cursor.fetchall()


def _text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise InvalidMunicipalRowError(field)
    return value


def _generation(rows: Sequence[Sequence[object]]) -> str:
    value = rows[0][0] if rows else None
    if not isinstance(value, datetime):
        raise InvalidMunicipalRowError("geracao")
    return value.strftime("%d%m%Y%H%M")


def _candidate(row: Sequence[object]) -> CandidateRow:
    return CandidateRow(
        uf=_text(row[0], "sg_uf"),
        ue=_text(row[1], "sg_ue"),
        nome_ue=_text(row[2], "nm_ue"),
        tipo_eleicao=parse_int(_text(row[3], "cd_tipo_eleicao"), "cd_tipo_eleicao"),
        data_eleicao=parse_tse_date(_text(row[4], "dt_eleicao"), "dt_eleicao"),
        turno=parse_int(_text(row[5], "nr_turno"), "nr_turno"),
        cargo=parse_int(_text(row[6], "cd_cargo"), "cd_cargo"),
        sq_candidato=_text(row[7], "sq_candidato"),
        nome_urna=_text(row[8], "nm_urna_candidato"),
        partido=parse_int(_text(row[9], "nr_partido"), "nr_partido"),
        sigla=_text(row[10], "sg_partido"),
        situacao=parse_int(_text(row[11], "cd_sit_tot_turno"), "cd_sit_tot_turno"),
    )


def _electorate(row: Sequence[object]) -> ElectorateRow:
    return ElectorateRow(
        uf=_text(row[0], "sg_uf"),
        ue=_text(row[1], "sg_ue"),
        nome_ue=_text(row[2], "nm_ue"),
        tipo_eleicao=parse_int(_text(row[3], "cd_tipo_eleicao"), "cd_tipo_eleicao"),
        turno=parse_int(_text(row[4], "nr_turno"), "nr_turno"),
        cargo=parse_int(_text(row[5], "cd_cargo"), "cd_cargo"),
        aptos=parse_int(_text(row[6], "qt_aptos"), "qt_aptos"),
    )


def _seat(row: Sequence[object]) -> SeatRow:
    return SeatRow(
        uf=_text(row[0], "sg_uf"),
        ue=_text(row[1], "sg_ue"),
        tipo_eleicao=parse_int(_text(row[2], "cd_tipo_eleicao"), "cd_tipo_eleicao"),
        cargo=parse_int(_text(row[3], "cd_cargo"), "cd_cargo"),
        vagas=parse_int(_text(row[4], "qt_vaga"), "qt_vaga"),
    )


def _mayor_rows(year: int, built: MunicipalBuild) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for item in built.municipios:
        mayor = item.prefeito
        base: tuple[object, ...] = (
            year,
            item.uf,
            item.ue,
            item.nome,
            item.eleitorado,
            item.vagas_vereador,
        )
        if mayor is None:
            rows.append((*base, None, None, None, None, None, None, "f"))
            continue
        rows.append(
            (
                *base,
                mayor.partido,
                mayor.sigla,
                mayor.nome_urna,
                mayor.sq_candidato,
                mayor.data_eleicao.isoformat(),
                mayor.turno,
                "t" if mayor.suplementar else "f",
            )
        )
    return rows


def _council_rows(year: int, built: MunicipalBuild) -> list[tuple[object, ...]]:
    return [
        (year, item.uf, item.ue, item.partido, item.sigla, item.eleitos)
        for item in built.vereadores
    ]


def _copy(cursor: SqlCursor, table: str, columns: str, rows: list[tuple[object, ...]]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    for row in rows:
        writer.writerow("" if value is None else value for value in row)
    with cursor.copy(f"COPY {table} ({columns}) FROM STDIN (FORMAT CSV)") as stream:
        stream.write(buffer.getvalue().encode("utf-8"))
