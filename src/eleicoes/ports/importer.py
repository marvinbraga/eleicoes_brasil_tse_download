from typing import Protocol

from eleicoes.domain.importing import ImportCommand, ImportReport


class ElectionImporter(Protocol):
    def execute(self, command: ImportCommand) -> ImportReport: ...

    def close(self) -> None: ...
