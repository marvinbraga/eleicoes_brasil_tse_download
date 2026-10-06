"""Port for municipality names used by the party-share grid."""

from collections.abc import Mapping
from typing import Protocol


class MunicipalityNames(Protocol):
    def names(self, uf: str) -> Mapping[int, str]: ...

    def close(self) -> None: ...
