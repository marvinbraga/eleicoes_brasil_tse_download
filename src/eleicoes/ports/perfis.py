"""Ports for municipal profiles. The core never sees an array."""

from dataclasses import dataclass
from typing import Protocol

from eleicoes.domain.errors import InconsistentCellError
from eleicoes.domain.perfis import GroupSpan, ProfileLine


@dataclass(frozen=True, slots=True)
class RawClusterFit:
    assignments: tuple[int, ...]
    centers: tuple[tuple[float, ...], ...]
    silhouette: float | None

    def __post_init__(self) -> None:
        if not self.assignments or not self.centers:
            raise InconsistentCellError()
        width = len(self.centers[0])
        if any(len(center) != width for center in self.centers):
            raise InconsistentCellError()
        if any(label < 0 or label >= len(self.centers) for label in self.assignments):
            raise InconsistentCellError()


class ProfileSource(Protocol):
    def profile_lines(self, ano: int, turno: int, cargo: str) -> tuple[ProfileLine, ...]: ...

    def close(self) -> None: ...


class ProfileClusterer(Protocol):
    def fit(
        self,
        matrix: tuple[tuple[float, ...], ...],
        span: GroupSpan,
    ) -> RawClusterFit: ...
