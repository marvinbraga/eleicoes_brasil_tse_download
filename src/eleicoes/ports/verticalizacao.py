"""Port for the stored power lines that feed the verticalization report."""

from typing import Protocol

from eleicoes.domain.verticalizacao import VerticalLine


class VerticalSource(Protocol):
    def vertical_lines(self, ano: int, turno: int) -> tuple[VerticalLine, ...]: ...

    def close(self) -> None: ...
