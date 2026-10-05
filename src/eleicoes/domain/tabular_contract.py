"""Contratos dos CSV de correspondência. O nome do membro escolhe o contrato."""

from dataclasses import dataclass
from pathlib import PurePosixPath

_SHARED = (
    "DT_GERACAO",
    "HH_GERACAO",
    "AA_ELEICAO",
    "CD_PLEITO",
    "SG_UF",
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
)
_AFTER_SECTION = (
    "NR_URNA_ESPERADA",
    "CD_CARGA_URNA_ESPERADA",
    "CD_FLASHCARD_URNA_ESPERADA",
    "DT_CARGA_URNA_ESPERADA",
    "ST_CORRESP_ALTERADA",
    "NM_MAQUINA_GERACAO_MIDIA",
    "NR_SRI_TPM_GERACAO_MIDIA",
    "NR_SRI_INSTAL_GERACAO_MIDIA",
    "NM_MAQUINA_TRANSM_CORRESP",
    "NR_SRI_TPM_TRANSM_CORRESP",
    "NR_SRI_INSTAL_TRANSM_CORRESP",
)


@dataclass(frozen=True, slots=True)
class TabularContract:
    table: str
    columns: tuple[str, ...]


CSEC = TabularContract(
    table="csec",
    columns=(*_SHARED, "NR_SECAO", "NR_LOCAL_VOTACAO", *_AFTER_SECTION),
)
CCONT = TabularContract(table="ccont", columns=(*_SHARED, *_AFTER_SECTION))


def contract_for(member_name: str) -> TabularContract | None:
    base = PurePosixPath(member_name).name.lower()
    if base.startswith("csec_") and base.endswith(".csv"):
        return CSEC
    if base.startswith("ccont_") and base.endswith(".csv"):
        return CCONT
    return None
