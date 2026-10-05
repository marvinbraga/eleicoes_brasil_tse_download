from pathlib import Path

from eleicoes.domain.errors import MissingElectionYearError
from eleicoes.domain.importing import ImportCommand
from eleicoes.domain.values import ElectionYear


class ImportCommandBuilder:
    """Monta o pedido de importação a partir do ano e da pasta do índice."""

    def __init__(self) -> None:
        self._year: ElectionYear | None = None
        self._origin: Path | None = None

    def with_year(self, year: ElectionYear) -> "ImportCommandBuilder":
        self._year = year
        return self

    def with_origin(self, origin: Path | None) -> "ImportCommandBuilder":
        self._origin = origin
        return self

    def build(self) -> ImportCommand:
        if self._year is None:
            raise MissingElectionYearError()
        origin = self._origin
        if origin is None:
            origin = Path("downloads") / str(self._year.value)
        return ImportCommand(year=self._year, origin=origin)
