from typing import Protocol

from eleicoes.domain.importing import ImportStatus, Provenance
from eleicoes.domain.tabular_contract import TabularContract


class TabularSink(Protocol):
    def ensure_model(self) -> None: ...

    def replace_member(
        self,
        contract: TabularContract,
        provenance: Provenance,
        csv_bytes: bytes,
    ) -> int: ...

    def record(
        self,
        provenance: Provenance,
        status: ImportStatus,
        linhas: int,
        tabela: str,
    ) -> None: ...

    def close(self) -> None: ...
