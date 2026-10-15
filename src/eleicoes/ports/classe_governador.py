"""Port for the governor-class tree. Training stays outside the domain."""

from dataclasses import dataclass
from typing import Protocol

from eleicoes.domain.classe_governador import ClassLine, ClassRule
from eleicoes.domain.errors import InconsistentCellError
from eleicoes.domain.presidente_governador import CLASS_ORDER


@dataclass(frozen=True, slots=True)
class ClassFit:
    majority: str
    expected: tuple[str, ...]
    predicted: tuple[str, ...]
    rules: tuple[ClassRule, ...]

    def __post_init__(self) -> None:
        if self.majority not in CLASS_ORDER:
            raise InconsistentCellError()
        if not self.expected or len(self.expected) != len(self.predicted):
            raise InconsistentCellError()


class ClassSource(Protocol):
    def class_lines(self, ano: int, turno: int) -> tuple[ClassLine, ...]: ...

    def close(self) -> None: ...


class GovernorClassModel(Protocol):
    def fit(
        self,
        matrix: tuple[tuple[float, ...], ...],
        labels: tuple[str, ...],
        parties: tuple[int, ...],
    ) -> ClassFit: ...
