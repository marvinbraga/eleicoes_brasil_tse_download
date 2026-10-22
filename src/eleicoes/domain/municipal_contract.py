"""Contratos dos CSV municipais do TSE. Só os membros por UF; o _BRASIL repete todos."""

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from re import compile as compile_pattern
from typing import Final

from eleicoes.domain.errors import InvalidGenerationError, InvalidMunicipalYearError
from eleicoes.domain.tabular_contract import TabularContract
from eleicoes.domain.values import UF_CODES, ElectionYear

MUNICIPAL_COLLECTION: Final = "municipais"
MUNICIPAL_UFS: Final = frozenset(code for code in UF_CODES if code not in {"DF", "ZZ"})
_MUNICIPAL_CYCLE: Final = 4
_HEAD_BYTES: Final = 64 * 1024
_MEMBER: Final = compile_pattern(
    r"^(?P<conjunto>consulta_cand|consulta_vagas|detalhe_votacao_munzona)"
    r"_(?P<ano>\d{4})_(?P<uf>[A-Z]{2})\.csv$"
)
_ELECTION: Final = (
    "DT_GERACAO",
    "HH_GERACAO",
    "ANO_ELEICAO",
    "CD_TIPO_ELEICAO",
    "NM_TIPO_ELEICAO",
)

CONSULTA_CAND: Final = TabularContract(
    table="consulta_cand",
    columns=(
        *_ELECTION,
        "NR_TURNO",
        "CD_ELEICAO",
        "DS_ELEICAO",
        "DT_ELEICAO",
        "TP_ABRANGENCIA",
        "SG_UF",
        "SG_UE",
        "NM_UE",
        "CD_CARGO",
        "DS_CARGO",
        "SQ_CANDIDATO",
        "NR_CANDIDATO",
        "NM_CANDIDATO",
        "NM_URNA_CANDIDATO",
        "NM_SOCIAL_CANDIDATO",
        "NR_CPF_CANDIDATO",
        "DS_EMAIL",
        "CD_SITUACAO_CANDIDATURA",
        "DS_SITUACAO_CANDIDATURA",
        "TP_AGREMIACAO",
        "NR_PARTIDO",
        "SG_PARTIDO",
        "NM_PARTIDO",
        "NR_FEDERACAO",
        "NM_FEDERACAO",
        "SG_FEDERACAO",
        "DS_COMPOSICAO_FEDERACAO",
        "SQ_COLIGACAO",
        "NM_COLIGACAO",
        "DS_COMPOSICAO_COLIGACAO",
        "SG_UF_NASCIMENTO",
        "DT_NASCIMENTO",
        "NR_TITULO_ELEITORAL_CANDIDATO",
        "CD_GENERO",
        "DS_GENERO",
        "CD_GRAU_INSTRUCAO",
        "DS_GRAU_INSTRUCAO",
        "CD_ESTADO_CIVIL",
        "DS_ESTADO_CIVIL",
        "CD_COR_RACA",
        "DS_COR_RACA",
        "CD_OCUPACAO",
        "DS_OCUPACAO",
        "CD_SIT_TOT_TURNO",
        "DS_SIT_TOT_TURNO",
    ),
)
DETALHE_VOTACAO_MUNZONA: Final = TabularContract(
    table="detalhe_votacao_munzona",
    columns=(
        *_ELECTION,
        "NR_TURNO",
        "CD_ELEICAO",
        "DS_ELEICAO",
        "DT_ELEICAO",
        "TP_ABRANGENCIA",
        "SG_UF",
        "SG_UE",
        "NM_UE",
        "CD_MUNICIPIO",
        "NM_MUNICIPIO",
        "NR_ZONA",
        "CD_CARGO",
        "DS_CARGO",
        "QT_APTOS",
        "QT_SECOES_PRINCIPAIS",
        "QT_SECOES_AGREGADAS",
        "QT_SECOES_NAO_INSTALADAS",
        "QT_TOTAL_SECOES",
        "QT_COMPARECIMENTO",
        "QT_ELEITORES_SECOES_NAO_INSTALADAS",
        "QT_ABSTENCOES",
        "ST_VOTO_EM_TRANSITO",
        "QT_VOTOS",
        "QT_VOTOS_CONCORRENTES",
        "QT_TOTAL_VOTOS_VALIDOS",
        "QT_VOTOS_NOMINAIS_VALIDOS",
        "QT_TOTAL_VOTOS_LEG_VALIDOS",
        "QT_VOTOS_LEG_VALIDOS",
        "QT_VOTOS_NOM_CONVR_LEG_VALIDOS",
        "QT_TOTAL_VOTOS_ANULADOS",
        "QT_VOTOS_NOMINAIS_ANULADOS",
        "QT_VOTOS_LEGENDA_ANULADOS",
        "QT_TOTAL_VOTOS_ANUL_SUBJUD",
        "QT_VOTOS_NOMINAIS_ANUL_SUBJUD",
        "QT_VOTOS_LEGENDA_ANUL_SUBJUD",
        "QT_VOTOS_BRANCOS",
        "QT_TOTAL_VOTOS_NULOS",
        "QT_VOTOS_NULOS",
        "QT_VOTOS_NULOS_TECNICOS",
        "QT_VOTOS_ANULADOS_APU_SEP",
        "HH_ULTIMA_TOTALIZACAO",
        "DT_ULTIMA_TOTALIZACAO",
    ),
)
CONSULTA_VAGAS: Final = TabularContract(
    table="consulta_vagas",
    columns=(
        *_ELECTION,
        "CD_ELEICAO",
        "DS_ELEICAO",
        "DT_ELEICAO",
        "DT_POSSE",
        "SG_UF",
        "SG_UE",
        "NM_UE",
        "CD_CARGO",
        "DS_CARGO",
        "QT_VAGA",
    ),
)
_BY_DATASET: Final = {
    "consulta_cand": CONSULTA_CAND,
    "consulta_vagas": CONSULTA_VAGAS,
    "detalhe_votacao_munzona": DETALHE_VOTACAO_MUNZONA,
}


@dataclass(frozen=True, slots=True)
class MunicipalMember:
    contract: TabularContract
    uf: str


@dataclass(frozen=True, slots=True)
class MunicipalArchive:
    package: str
    filename: str


def require_municipal_year(year: ElectionYear) -> ElectionYear:
    if year.value % _MUNICIPAL_CYCLE != 0:
        raise InvalidMunicipalYearError(year.value)
    return year


def municipal_archives(year: ElectionYear) -> tuple[MunicipalArchive, ...]:
    value = require_municipal_year(year).value
    return (
        MunicipalArchive(f"candidatos-{value}", f"consulta_cand_{value}.zip"),
        MunicipalArchive(f"candidatos-{value}", f"consulta_vagas_{value}.zip"),
        MunicipalArchive(f"resultados-{value}", f"detalhe_votacao_munzona_{value}.zip"),
    )


def municipal_member(member_name: str, year: int) -> MunicipalMember | None:
    found = _MEMBER.fullmatch(PurePosixPath(member_name).name)
    if found is None or int(found.group("ano")) != year:
        return None
    uf = found.group("uf")
    if uf not in MUNICIPAL_UFS:
        return None
    return MunicipalMember(contract=_BY_DATASET[found.group("conjunto")], uf=uf)


def generation_from_csv(member: str, csv_bytes: bytes) -> str:
    """DT_GERACAO e HH_GERACAO da primeira linha, no carimbo DDMMAAAAHHMM de raw.carga."""
    text = io.StringIO(csv_bytes[:_HEAD_BYTES].decode("latin-1"), newline="")
    reader = csv.reader(text, delimiter=";")
    header = next(reader, None)
    first = next(reader, None)
    if header is None or first is None or header[:2] != ["DT_GERACAO", "HH_GERACAO"]:
        raise InvalidGenerationError(member)
    if len(first) < 2:
        raise InvalidGenerationError(member)
    try:
        at = datetime.strptime(f"{first[0]} {first[1]}", "%d/%m/%Y %H:%M:%S")
    except ValueError as exc:
        raise InvalidGenerationError(member) from exc
    return at.strftime("%d%m%Y%H%M")


def expected_members(year: int) -> tuple[str, ...]:
    """Os 3 conjuntos × 26 UFs que precisam estar carregados para reconstruir a análise."""
    return tuple(
        f"{conjunto}_{year}_{uf}.csv" for conjunto in _BY_DATASET for uf in sorted(MUNICIPAL_UFS)
    )
