from typing import Protocol

from eleicoes.domain.forca_municipal import MunicipalCountsByUf, StoredMunicipalResults
from eleicoes.domain.importing import ImportCommand
from eleicoes.domain.municipais import MunicipalBuild, MunicipalImportReport, MunicipalRaw


class MunicipalStore(Protocol):
    def read_raw(self, year: int) -> MunicipalRaw: ...

    def save(self, year: int, built: MunicipalBuild) -> None: ...

    def close(self) -> None: ...


class MunicipalImporter(Protocol):
    def execute(self, command: ImportCommand) -> MunicipalImportReport: ...

    def close(self) -> None: ...


class AsyncMunicipalResultsReader(Protocol):
    async def load(self, ano: int, uf: str | None) -> StoredMunicipalResults | None:
        """None quando analise.municipal_carga não tem o ano. Com uf, traz os municípios."""
        ...

    async def party_counts_by_uf(self, ano: int) -> MunicipalCountsByUf | None:
        """Contagens por (UF, partido) e totais por UF numa leitura só; None sem importação."""
        ...
