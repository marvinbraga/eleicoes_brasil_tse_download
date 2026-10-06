"""Port for boletim consultations. The adapter is chosen at the edge."""

from typing import Protocol

from eleicoes.domain.boletim_consulta import (
    BlankNullProjection,
    BrancosNulos,
    Comparativo,
    LinhaVoto,
    NominalProjection,
    Participacao,
    PoderPartido,
    PrimeiroColocado,
    SectionProjection,
    TotalCargo,
    VotosMunicipio,
    VotosZona,
)


class BoletimReader(Protocol):
    def totals(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[TotalCargo, ...]: ...

    def municipalities(
        self, ano: int, turno: int, uf: str, cargo: str, numero: int
    ) -> tuple[VotosMunicipio, ...]: ...

    def comparison(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        primeiro: int,
        segundo: int,
        nivel: str,
    ) -> tuple[Comparativo, ...]: ...

    def party_power(
        self, ano: int, turno: int, ufs: tuple[str, ...], cargo: str, nivel: str
    ) -> tuple[PoderPartido, ...]: ...

    def participation(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[Participacao, ...]: ...

    def blank_and_null(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[BrancosNulos, ...]: ...

    def leading_candidate(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[PrimeiroColocado, ...]: ...

    def section_lines(
        self, ano: int, turno: int, uf: str, municipio: int, zona: int, secao: int
    ) -> tuple[LinhaVoto, ...]: ...

    def zones(
        self, ano: int, turno: int, uf: str, municipio: int, cargo: str, numero: int
    ) -> tuple[VotosZona, ...]: ...

    def section_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[SectionProjection, ...]: ...

    def nominal_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[NominalProjection, ...]: ...

    def blank_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[BlankNullProjection, ...]: ...

    def present_ufs(self, ano: int, turno: int, cargo: str) -> tuple[str, ...]: ...

    def close(self) -> None: ...
