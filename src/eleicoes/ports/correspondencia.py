"""Port for correspondence consultations. The adapter is chosen at the edge."""

from typing import Protocol

from eleicoes.domain.correspondencia import (
    Contingencia,
    MudancaGeracao,
    ProjecaoContingencia,
    ProjecaoSecao,
    ResumoUf,
    Secao,
    StatusCorrespondencia,
)


class CorrespondenciaReader(Protocol):
    def secoes(self, uf: str | None, status: StatusCorrespondencia | None) -> tuple[Secao, ...]: ...

    def contingencias(
        self, uf: str | None, status: StatusCorrespondencia | None
    ) -> tuple[Contingencia, ...]: ...

    def resumos(self) -> tuple[ResumoUf, ...]: ...

    def mudancas(self, uf: str | None) -> tuple[MudancaGeracao, ...]: ...

    def geracoes(self, uf: str, zona: int | None, secao: int | None) -> tuple[Secao, ...]: ...

    def projecoes(self, uf: str | None) -> tuple[ProjecaoSecao, ...]: ...

    def projecoes_contingencia(self, uf: str | None) -> tuple[ProjecaoContingencia, ...]: ...

    def close(self) -> None: ...
