"""Write the four party-power grids and hand the file to the caller."""

import argparse
import sys
import webbrowser
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from eleicoes.adapters.html_grade import html_das_grades
from eleicoes.consultas.grade import grade_de_poder
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.grade import GradeDePoder
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.ports.relatorio_poder import RelatorioPoderStore
from eleicoes.use_cases.failure import failure_line

_FAILURE: Final = "Não foi possível apresentar os relatórios."
_LEVELS: Final[tuple[str, ...]] = ("municipio", "uf", "regiao", "pais")
_LABELS: Final[dict[str, str]] = {
    "municipio": "Por município",
    "uf": "Por estado",
    "regiao": "Por região",
    "pais": "No país",
}

GradeLoader = Callable[[int, int, str, str, str], GradeDePoder]
GradeRenderer = Callable[[tuple[GradeDePoder, ...]], str]
ReportOpener = Callable[[Path], bool]


@dataclass(frozen=True, slots=True)
class PresentedReport:
    caminho: Path
    grades: tuple[GradeDePoder, ...]
    aberto: bool


class PresentPartyGrades:
    def __init__(
        self,
        load: GradeLoader,
        render: GradeRenderer,
        open_report: ReportOpener,
    ) -> None:
        self._load = load
        self._render = render
        self._open = open_report

    def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        destino: Path,
    ) -> PresentedReport:
        grades = self._grades(ano, turno, uf, cargo)
        opened = self.publish(destino, self._render(grades))
        return PresentedReport(destino, grades, opened)

    def publish(self, destino: Path, html: str) -> bool:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(html, encoding="utf-8")
        return self._open(destino)

    def publish_grades(self, grades: tuple[GradeDePoder, ...], destino: Path) -> bool:
        return self.publish(destino, self._render(grades))

    def _grades(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
    ) -> tuple[GradeDePoder, ...]:
        return tuple(self._load(ano, turno, uf, cargo, nivel) for nivel in _LEVELS)


def default_presenter(open_report: ReportOpener | None = None) -> PresentPartyGrades:
    return PresentPartyGrades(_load_grade, html_das_grades, open_report or _open_browser)


def _load_grade(ano: int, turno: int, uf: str, cargo: str, nivel: str) -> GradeDePoder:
    return grade_de_poder(ano, turno, uf, cargo, nivel=nivel)


def _open_browser(path: Path) -> bool:
    return webbrowser.open(path.resolve().as_uri())


def main(
    argv: Sequence[str] | None = None,
    *,
    presenter: PresentPartyGrades | None = None,
    store: RelatorioPoderStore | None = None,
) -> int:
    args = _parser().parse_args(argv)
    destino = _destino(args.ano, args.turno, args.uf, args.cargo, args.destino)
    try:
        text = _present(args, destino, presenter, store)
    except ElectionError as exc:
        print(failure_line(_FAILURE, exc), file=sys.stderr)
        return EXIT_FAILURE
    print(text)
    return EXIT_SUCCESS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apresenta o poder do partido por município, estado, região e país.",
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--turno", type=int, default=1)
    parser.add_argument("--uf", default="AC")
    parser.add_argument("--cargo", default="deputadoFederal")
    parser.add_argument("--destino")
    parser.add_argument("--sem-navegador", action="store_true")
    parser.add_argument(
        "--atualizar",
        action="store_true",
        help="Recalcula as grades e substitui o relatório gravado no banco.",
    )
    return parser


def _destino(ano: int, turno: int, uf: str, cargo: str, informed: str | None) -> Path:
    if informed:
        return Path(informed)
    name = f"{uf.strip().lower()}-{ano}-turno-{turno}-{cargo}.html"
    return Path("relatorios") / name


def _opener(skip_browser: bool) -> ReportOpener:
    if skip_browser:
        return _skip_browser
    return _open_browser


def _skip_browser(_path: Path) -> bool:
    return True


def _present(
    args: argparse.Namespace,
    destino: Path,
    presenter: PresentPartyGrades | None,
    store: RelatorioPoderStore | None,
) -> str:
    if presenter is not None and store is None:
        report = presenter.execute(args.ano, args.turno, args.uf, args.cargo, destino)
        return _message(report)
    return _cached(args, destino, presenter, store)


def _cached(
    args: argparse.Namespace,
    destino: Path,
    presenter: PresentPartyGrades | None,
    store: RelatorioPoderStore | None,
) -> str:
    from eleicoes.use_cases.apresentar_relatorio_poder import PresentPowerReport

    cache = store if store is not None else _production_store()
    tool = presenter if presenter is not None else default_presenter(_opener(args.sem_navegador))
    try:
        view = PresentPowerReport(tool, cache).execute(
            args.ano,
            args.turno,
            args.uf,
            args.cargo,
            destino,
            atualizar=bool(args.atualizar),
        )
    finally:
        cache.close()
    return _cached_message(view.path, view.summary, view.opened, view.loaded, view.generated_at)


def _production_store() -> RelatorioPoderStore:
    from eleicoes.composition.grade import build_power_report_store

    return build_power_report_store()


def _cached_message(
    caminho: Path,
    resumo: str,
    aberto: bool,
    loaded: bool,
    gerado_em: datetime,
) -> str:
    lines: list[str] = []
    if loaded:
        lines.append(_loaded_line(gerado_em))
    lines.append(f"Relatórios apresentados: {caminho.resolve()}")
    lines.append(resumo)
    if not aberto:
        lines.append("Não foi possível abrir o navegador.")
    if not loaded:
        lines.append("Relatório gravado no banco.")
    return "\n".join(lines)


def _loaded_line(moment: datetime) -> str:
    stamp = moment.astimezone().strftime("%Y-%m-%d %H:%M")
    return f"Relatório carregado do banco, gerado em {stamp}."


def _message(report: PresentedReport) -> str:
    lines = [
        f"Relatórios apresentados: {report.caminho.resolve()}",
        grade_summary(report.grades),
    ]
    if not report.aberto:
        lines.append("Não foi possível abrir o navegador.")
    return "\n".join(lines)


def grade_summary(grades: tuple[GradeDePoder, ...]) -> str:
    return "\n".join(_summary(grade) for grade in grades)


def _summary(grade: GradeDePoder) -> str:
    places = _count(len(grade.linhas), "lugar", "lugares")
    parties = _count(len(grade.colunas), "partido", "partidos")
    return f"{_LABELS[grade.nivel]}: {places}, {parties}."


def _count(amount: int, singular: str, plural: str) -> str:
    word = singular if amount == 1 else plural
    return f"{amount} {word}"
