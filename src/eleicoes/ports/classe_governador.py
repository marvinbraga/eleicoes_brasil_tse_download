"""Port for the governor-class tree. Training stays outside the domain."""

from dataclasses import dataclass
from typing import Protocol

from eleicoes.domain.classe_governador import ClassLine, ClassRule
from eleicoes.domain.errors import InconsistentCellError
from eleicoes.domain.presidente_governador import CLASS_ORDER


@dataclass(frozen=True, slots=True)
class ClassFit:
    predicted: tuple[str, ...]
    rules: tuple[ClassRule, ...]

    def __post_init__(self) -> None:
        if not self.predicted:
            raise InconsistentCellError()
        if any(label not in CLASS_ORDER for label in self.predicted):
            raise InconsistentCellError()


class ClassSource(Protocol):
    def class_lines(self, ano: int, turno: int) -> tuple[ClassLine, ...]: ...

    def municipal_ufs(self, ano: int, turno: int) -> tuple[tuple[str, str], ...]: ...

    def close(self) -> None: ...


class GovernorClassModel(Protocol):
    def fit(
        self,
        matrix: tuple[tuple[float, ...], ...],
        labels: tuple[str, ...],
        parties: tuple[int, ...],
        groups: tuple[str, ...],
    ) -> ClassFit: ...
