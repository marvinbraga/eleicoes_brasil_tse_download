"""Port for the stored party-power grades."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from eleicoes.domain.errors import InvalidStoredReportError
from eleicoes.domain.stored_grade import StoredCell


@dataclass(frozen=True, slots=True)
class StoredReport:
    cells: tuple[StoredCell, ...]
    gerado_em: datetime

    def __post_init__(self) -> None:
        if self.gerado_em.tzinfo is None:
            raise InvalidStoredReportError("gerado_em")


class RelatorioPoderStore(Protocol):
    def load(self, ano: int, turno: int, cargo: str) -> StoredReport | None: ...

    def save(
        self,
        ano: int,
        turno: int,
        cargo: str,
        cells: tuple[StoredCell, ...],
    ) -> datetime: ...

    def close(self) -> None: ...


class AsyncRelatorioPoderStore(Protocol):
    async def load(self, ano: int, turno: int, cargo: str) -> StoredReport | None: ...

    async def save(
        self,
        ano: int,
        turno: int,
        cargo: str,
        cells: tuple[StoredCell, ...],
    ) -> datetime: ...

    async def load_levels(
        self,
        ano: int,
        turno: int,
        cargo: str,
        niveis: tuple[str, ...],
    ) -> StoredReport | None: ...
