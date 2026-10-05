from dataclasses import dataclass
from typing import Protocol

from eleicoes.domain.errors import CkanPayloadError
from eleicoes.domain.values import RemoteZip


@dataclass(frozen=True, slots=True)
class CkanPackage:
    name: str
    groups: tuple[str, ...]
    archives: tuple[RemoteZip, ...]


@dataclass(frozen=True, slots=True)
class CkanPage:
    total: int
    packages: tuple[CkanPackage, ...]

    def __post_init__(self) -> None:
        if isinstance(self.total, bool) or self.total < 0:
            raise CkanPayloadError("CKAN page total is invalid")


class CkanGateway(Protocol):
    def package_show(self, package_id: str) -> CkanPackage | None: ...

    def package_search(self, query: str, *, start: int, rows: int) -> CkanPage: ...
