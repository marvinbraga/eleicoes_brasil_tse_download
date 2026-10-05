from dataclasses import dataclass
from enum import Enum
from typing import Final

EXIT_SUCCESS: Final = 0
EXIT_FAILURE: Final = 1
EXIT_NOT_PUBLISHED: Final = 2


class TransferStatus(Enum):
    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class FileOutcome:
    filename: str
    status: TransferStatus


@dataclass(frozen=True, slots=True)
class RunReport:
    outcomes: tuple[FileOutcome, ...]

    @property
    def discovered(self) -> int:
        return len(self.outcomes)

    @property
    def downloaded(self) -> int:
        return self._count(TransferStatus.DOWNLOADED)

    @property
    def skipped(self) -> int:
        return self._count(TransferStatus.SKIPPED)

    @property
    def missing(self) -> int:
        return self._count(TransferStatus.MISSING)

    @property
    def exit_code(self) -> int:
        if self.discovered == 0:
            return EXIT_NOT_PUBLISHED
        return EXIT_SUCCESS

    def _count(self, status: TransferStatus) -> int:
        return sum(1 for item in self.outcomes if item.status is status)
