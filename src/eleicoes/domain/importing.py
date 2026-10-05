"""Pedido, proveniência e resultado da importação tabular."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from re import compile as compile_pattern

from eleicoes.domain.errors import InvalidGenerationError
from eleicoes.domain.report import EXIT_FAILURE, EXIT_NOT_PUBLISHED, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear

_STAMP = compile_pattern(r"_(\d{12})$")
_STAMP_FORMAT = "%d%m%Y%H%M"


class ImportStatus(Enum):
    LOADED = "loaded"
    IGNORED = "ignored"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Generation:
    """Carimbo DDMMAAAAHHMM. A ordem é cronológica, não alfabética."""

    stamp: str
    at: datetime

    @classmethod
    def from_filename(cls, name: str) -> "Generation":
        stem = Path(name).name
        if "." in stem:
            stem = stem.rsplit(".", 1)[0]
        found = _STAMP.search(stem)
        if found is None:
            raise InvalidGenerationError(name)
        stamp = found.group(1)
        try:
            parsed = datetime.strptime(stamp, _STAMP_FORMAT)
        except ValueError as exc:
            raise InvalidGenerationError(name) from exc
        return cls(stamp=stamp, at=parsed)


@dataclass(frozen=True, slots=True)
class Provenance:
    arquivo: str
    membro: str
    geracao: str
    conjunto: str
    turno: str
    uf: str


@dataclass(frozen=True, slots=True)
class IndexEntry:
    conjunto: str
    turno: str
    uf: str
    arquivo: str
    path: Path


@dataclass(frozen=True, slots=True)
class ImportCommand:
    year: ElectionYear
    origin: Path


@dataclass(frozen=True, slots=True)
class MemberOutcome:
    arquivo: str
    membro: str
    status: ImportStatus
    linhas: int
    tabela: str


@dataclass(frozen=True, slots=True)
class ImportReport:
    outcomes: tuple[MemberOutcome, ...]

    def count(self, status: ImportStatus) -> int:
        return sum(1 for item in self.outcomes if item.status is status)

    @property
    def loaded_rows(self) -> int:
        return sum(item.linhas for item in self.outcomes if item.status is ImportStatus.LOADED)

    @property
    def exit_code(self) -> int:
        if self.count(ImportStatus.FAILED) > 0:
            return EXIT_FAILURE
        if self.count(ImportStatus.LOADED) > 0:
            return EXIT_SUCCESS
        return EXIT_NOT_PUBLISHED
