"""HTML reports for the API. The cache is the store; the browser stays closed."""

from eleicoes.adapters.html_grade import html_das_grades
from eleicoes.adapters.html_presidente_governador import html_presidente_governador
from eleicoes.domain.boletim_consulta import require_cargo
from eleicoes.domain.presidente_governador import view_from_places
from eleicoes.domain.stored_grade import cells_from_grades, grades_from_cells
from eleicoes.domain.values import ElectionYear, Turno, Uf
from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.ports.grade import AsyncMunicipalityNames
from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore
from eleicoes.ports.relatorio_presidente_governador import AsyncRelatorioPresidenteGovernadorStore
from eleicoes.use_cases.grade_async import build_all_grades
from eleicoes.use_cases.presidente_governador_async import collect_places


class RenderPowerReport:
    def __init__(
        self,
        reader: AsyncBoletimReader,
        names: AsyncMunicipalityNames,
        store: AsyncRelatorioPoderStore,
    ) -> None:
        self._reader = reader
        self._names = names
        self._store = store

    async def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        *,
        atualizar: bool = False,
    ) -> str:
        year, turn, code, office = _power_scope(ano, turno, uf, cargo)
        if not atualizar:
            stored = await self._store.load(year, turn, office)
            if stored is not None:
                return html_das_grades(grades_from_cells(year, turn, code, office, stored.cells))
        grades = await build_all_grades(self._reader, self._names, year, turn, code, office)
        await self._store.save(year, turn, office, cells_from_grades(grades))
        return html_das_grades(grades)


class RenderPresidentGovernorReport:
    def __init__(
        self,
        reader: AsyncBoletimReader,
        names: AsyncMunicipalityNames,
        store: AsyncRelatorioPresidenteGovernadorStore,
    ) -> None:
        self._reader = reader
        self._names = names
        self._store = store

    async def execute(self, ano: int, turno: int, uf: str, *, atualizar: bool = False) -> str:
        year, turn = _cross_scope(ano, turno, uf)
        if not atualizar:
            stored = await self._store.load(year, turn)
            if stored is not None:
                return html_presidente_governador(view_from_places(year, turn, stored.places))
        places = await collect_places(self._reader, self._names, year, turn)
        await self._store.save(year, turn, places)
        return html_presidente_governador(view_from_places(year, turn, places))


def _power_scope(ano: int, turno: int, uf: str, cargo: str) -> tuple[int, int, str, str]:
    return ElectionYear(ano).value, Turno(turno).value, Uf(uf).code, require_cargo(cargo)


def _cross_scope(ano: int, turno: int, uf: str) -> tuple[int, int]:
    Uf(uf)
    return ElectionYear(ano).value, Turno(turno).value
