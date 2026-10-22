"""Port for the stored municipal cells the capillarity report reads."""

from typing import Protocol

from eleicoes.domain.stored_grade import StoredCell


class MunicipalCellSource(Protocol):
    def municipal_cells(self, ano: int, turno: int, cargo: str) -> tuple[StoredCell, ...]: ...

    def close(self) -> None: ...
