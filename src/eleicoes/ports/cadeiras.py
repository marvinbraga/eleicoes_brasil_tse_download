"""Port the força partidária scoreboard (plano 1) reads. Plano 2 implements it.

Shape agreed in docs/superpowers/plans/2026-10-22-placar-forca-partidaria.md (Fase B).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Federacao:
    # The federation code ("fe-brasil"), the same one in the row key "fed:<codigo>";
    # not the display sigla ("FE BRASIL").
    sigla: str
    nome: str
    partidos: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CadeirasUnidade:
    chave: str
    uf: str
    camara: int | None
    senado: int | None
    governador_1t: int | None
    governador_2t: int | None
    assembleia: int | None


@dataclass(frozen=True, slots=True)
class TotaisCadeiras:
    camara: int
    senado: int
    governadores: int
    assembleias: int


@dataclass(frozen=True, slots=True)
class EstimativaCadeiras:
    ano: int
    turno: int
    gerado_em: datetime
    federacoes: tuple[Federacao, ...]
    totais: TotaisCadeiras
    linhas: tuple[CadeirasUnidade, ...]


class AsyncEstimativaCadeiras(Protocol):
    async def load(self, ano: int, turno: int) -> EstimativaCadeiras | None: ...
