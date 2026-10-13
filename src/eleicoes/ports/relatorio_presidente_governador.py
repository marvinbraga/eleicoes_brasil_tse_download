"""Port for the stored president × governor municipal cells."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from eleicoes.domain.errors import InvalidStoredReportError
from eleicoes.domain.presidente_governador import MunicipalPlace


@dataclass(frozen=True, slots=True)
class StoredCrossReport:
    places: tuple[MunicipalPlace, ...]
    gerado_em: datetime

    def __post_init__(self) -> None:
        if self.gerado_em.tzinfo is None:
            raise InvalidStoredReportError("gerado_em")
        keys = tuple((place.uf, place.codigo) for place in self.places)
        if len(keys) != len(set(keys)):
            raise InvalidStoredReportError("codigo")


class RelatorioPresidenteGovernadorStore(Protocol):
    def load(self, ano: int, turno: int) -> StoredCrossReport | None: ...

    def save(
        self,
        ano: int,
        turno: int,
        places: tuple[MunicipalPlace, ...],
    ) -> datetime: ...

    def close(self) -> None: ...


class AsyncRelatorioPresidenteGovernadorStore(Protocol):
    async def load(self, ano: int, turno: int) -> StoredCrossReport | None: ...

    async def save(
        self,
        ano: int,
        turno: int,
        places: tuple[MunicipalPlace, ...],
    ) -> datetime: ...
