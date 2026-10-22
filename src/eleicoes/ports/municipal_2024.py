"""Porta do Placar (plano 1, fase C): prefeitos, eleitorado governado e vereadores de 2024."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class MunicipalPartido2024:
    partido: int  # número de 2026, já convertido pela equivalência (D12, equivalente_2026)
    uf: str  # "BR" ou uma das 26 UFs com eleição municipal (sem DF e sem ZZ)
    prefeitos: int  # prefeituras com prefeito do partido na data de corte
    eleitorado_governado: int  # eleitorado apto 2024 desses municípios (não é população)
    vereadores: int  # vereadores eleitos pelo partido


@dataclass(frozen=True, slots=True)
class TotaisMunicipal2024:
    uf: str  # "BR" ou uma das 26 UFs
    municipios: int  # 5.569 no país; inclui municípios sem prefeito eleito
    com_prefeito: int
    eleitorado: int  # 155.912.680 no país
    vereadores: int


@dataclass(frozen=True, slots=True)
class Municipal2024:
    data_corte: datetime  # DT_GERACAO dos CSV do TSE (D2)
    importado_em: datetime
    equivalencia_versao: str  # VERSAO_EQUIVALENCIA
    totais: tuple[TotaisMunicipal2024, ...]  # um por UF e um "BR"; denominadores (não somar linhas)
    linhas: tuple[MunicipalPartido2024, ...]
    sem_correspondencia: tuple[int, ...]  # números de 2024 sem número em 2026; só nos totais


class AsyncMunicipal2024(Protocol):
    async def load(self) -> Municipal2024 | None: ...
