"""Present the party-power HTML from stored grades, or calculate and store the cells."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from eleicoes.domain.errors import InvalidStoredReportError
from eleicoes.domain.stored_grade import cells_from_grades, grades_from_cells
from eleicoes.ports.relatorio_poder import RelatorioPoderStore, StoredReport
from eleicoes.use_cases.apresentar_grade import PresentPartyGrades, grade_summary


@dataclass(frozen=True, slots=True)
class PresentedPowerReport:
    path: Path
    summary: str
    opened: bool
    loaded: bool
    generated_at: datetime

    def __post_init__(self) -> None:
        if self.summary.strip() == "":
            raise InvalidStoredReportError("resumo")
        if self.generated_at.tzinfo is None:
            raise InvalidStoredReportError("gerado_em")


class PresentPowerReport:
    def __init__(self, presenter: PresentPartyGrades, store: RelatorioPoderStore) -> None:
        self._presenter = presenter
        self._store = store

    def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        destino: Path,
        *,
        atualizar: bool = False,
    ) -> PresentedPowerReport:
        if not atualizar:
            stored = self._store.load(ano, turno, cargo)
            if stored is not None:
                return self._reuse(ano, turno, uf, cargo, stored, destino)
        return self._calculate(ano, turno, uf, cargo, destino)

    def _reuse(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        stored: StoredReport,
        destino: Path,
    ) -> PresentedPowerReport:
        grades = grades_from_cells(ano, turno, uf, cargo, stored.cells)
        opened = self._presenter.publish_grades(grades, destino)
        return PresentedPowerReport(
            destino,
            grade_summary(grades),
            opened,
            True,
            stored.gerado_em,
        )

    def _calculate(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        destino: Path,
    ) -> PresentedPowerReport:
        report = self._presenter.execute(ano, turno, uf, cargo, destino)
        generated_at = self._store.save(ano, turno, cargo, cells_from_grades(report.grades))
        return PresentedPowerReport(
            destino,
            grade_summary(report.grades),
            report.aberto,
            False,
            generated_at,
        )
