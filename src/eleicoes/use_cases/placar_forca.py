"""Strength scoreboard from the stored power cells. Reads only the levels it needs."""

import asyncio

from eleicoes.domain.errors import MissingStrengthSourcesError
from eleicoes.domain.forca import FontesForca, PlacarForca, placar_forca, require_cargo_referencia
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore

_BASE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("presidente", ("pais", "uf")),
    ("deputadoFederal", ("pais", "uf")),
    ("deputadoEstadual", ("uf",)),
)
_MUNICIPIO = "municipio"
Cells = tuple[StoredCell, ...] | None


class MontarPlacarForca:
    def __init__(self, store: AsyncRelatorioPoderStore) -> None:
        self._store = store

    async def execute(self, ano: int, turno: int, cargo_referencia: str) -> PlacarForca:
        year = ElectionYear(ano).value
        turn = Turno(turno).value
        referencia = require_cargo_referencia(cargo_referencia)
        loaded: dict[str, Cells] = {}
        for cargo, niveis in _plano(referencia):
            loaded[cargo] = await self._cells(year, turn, cargo, niveis)
        if all(cells is None for cells in loaded.values()):
            raise MissingStrengthSourcesError(tuple(loaded))
        fontes = FontesForca(
            loaded["presidente"],
            loaded["deputadoFederal"],
            loaded["deputadoEstadual"],
            loaded[referencia],
        )
        return await asyncio.to_thread(placar_forca, year, turn, referencia, fontes)

    async def _cells(self, ano: int, turno: int, cargo: str, niveis: tuple[str, ...]) -> Cells:
        report = await self._store.load_levels(ano, turno, cargo, niveis)
        if report is None or not report.cells:
            return None
        return report.cells


def _plano(referencia: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    plano = tuple((cargo, _niveis(cargo, niveis, referencia)) for cargo, niveis in _BASE)
    if any(cargo == referencia for cargo, _base in _BASE):
        return plano
    return (*plano, (referencia, (_MUNICIPIO,)))


def _niveis(cargo: str, niveis: tuple[str, ...], referencia: str) -> tuple[str, ...]:
    return (*niveis, _MUNICIPIO) if cargo == referencia else niveis
