"""Portas do boletim: ler bytes e substituir uma UF."""

from collections.abc import Sequence
from typing import Protocol

from eleicoes.domain.boletim import Boletim, BoletimImportReport, ImportBoletinsCommand
from eleicoes.domain.values import ElectionYear, Turno, Uf


class BoletimReader(Protocol):
    def read(self, arquivo: str, payload: bytes) -> Boletim: ...


class BoletimSink(Protocol):
    def ensure_model(self) -> None: ...

    def replace_uf(
        self,
        year: ElectionYear,
        turno: Turno,
        uf: Uf,
        boletins: Sequence[Boletim],
    ) -> int: ...

    def close(self) -> None: ...


class BoletimImporter(Protocol):
    def execute(self, command: ImportBoletinsCommand) -> BoletimImportReport: ...

    def close(self) -> None: ...
