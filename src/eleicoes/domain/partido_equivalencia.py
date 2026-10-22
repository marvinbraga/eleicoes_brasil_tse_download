"""Correspondência versionada entre os partidos de 2024 e o registro de 2026. A chave é o número."""

from dataclasses import dataclass
from enum import Enum
from typing import Final

VERSAO_EQUIVALENCIA: Final = "2026-10-22"


class Correspondencia(Enum):
    MESMO = "mesmo"
    GRAFIA = "grafia"
    RENOMEADO = "renomeado"
    DIVERGENTE = "divergente"
    SEM_CORRESPONDENCIA = "sem_correspondencia"


@dataclass(frozen=True, slots=True)
class PartidoEquivalente:
    numero_2024: int
    sigla_2024: str
    numero_2026: int | None
    sigla_2026: str | None
    correspondencia: Correspondencia
    nota: str


def _mesmo(numero: int, sigla: str) -> PartidoEquivalente:
    return PartidoEquivalente(numero, sigla, numero, sigla, Correspondencia.MESMO, "")


TABELA_2024_2026: Final[tuple[PartidoEquivalente, ...]] = (
    _mesmo(10, "REPUBLICANOS"),
    _mesmo(11, "PP"),
    _mesmo(12, "PDT"),
    _mesmo(13, "PT"),
    _mesmo(15, "MDB"),
    _mesmo(16, "PSTU"),
    _mesmo(18, "REDE"),
    _mesmo(20, "PODE"),
    _mesmo(21, "PCB"),
    _mesmo(22, "PL"),
    _mesmo(23, "CIDADANIA"),
    _mesmo(25, "PRD"),
    _mesmo(27, "DC"),
    _mesmo(28, "PRTB"),
    _mesmo(29, "PCO"),
    _mesmo(30, "NOVO"),
    _mesmo(33, "MOBILIZA"),
    PartidoEquivalente(
        35,
        "PMB",
        35,
        "DEMOCRATA",
        Correspondencia.RENOMEADO,
        "O PMB passou a se chamar Democrata em 2/12/2025.",
    ),
    _mesmo(36, "AGIR"),
    _mesmo(40, "PSB"),
    _mesmo(43, "PV"),
    _mesmo(44, "UNIÃO"),
    _mesmo(45, "PSDB"),
    _mesmo(50, "PSOL"),
    _mesmo(55, "PSD"),
    PartidoEquivalente(
        65,
        "PC do B",
        65,
        "PCdoB",
        Correspondencia.GRAFIA,
        "Mesma legenda; o TSE grafa PC do B nos arquivos de 2024.",
    ),
    _mesmo(70, "AVANTE"),
    _mesmo(77, "SOLIDARIEDADE"),
    _mesmo(80, "UP"),
)
_POR_NUMERO: Final = {item.numero_2024: item for item in TABELA_2024_2026}


def equivalente_2026(numero: int, sigla_2024: str) -> PartidoEquivalente:
    known = _POR_NUMERO.get(numero)
    if known is None:
        return PartidoEquivalente(
            numero, sigla_2024, None, None, Correspondencia.SEM_CORRESPONDENCIA, ""
        )
    if known.sigla_2024 != sigla_2024:
        return PartidoEquivalente(
            numero,
            sigla_2024,
            known.numero_2026,
            known.sigla_2026,
            Correspondencia.DIVERGENTE,
            f"A sigla esperada para o número {numero} em 2024 era {known.sigla_2024}.",
        )
    return known
