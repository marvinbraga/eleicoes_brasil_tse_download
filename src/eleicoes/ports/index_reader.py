from pathlib import Path
from typing import Protocol

from eleicoes.domain.importing import IndexEntry


class IndexReader(Protocol):
    def downloaded(self, origin: Path) -> tuple[IndexEntry, ...]: ...
