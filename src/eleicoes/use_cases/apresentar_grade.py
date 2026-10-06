"""Write the four party-power grids and hand the file to the caller."""

import argparse
import sys
import webbrowser
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from eleicoes.adapters.html_grade import html_das_grades
from eleicoes.consultas.grade import grade_de_poder
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.grade import GradeDePoder
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS

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
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(self._render(grades), encoding="utf-8")
        return PresentedReport(destino, grades, self._open(destino))

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
) -> int:
    args = _parser().parse_args(argv)
    destino = _destino(args.ano, args.turno, args.uf, args.cargo, args.destino)
    tool = presenter if presenter is not None else default_presenter(_opener(args.sem_navegador))
    try:
        report = tool.execute(args.ano, args.turno, args.uf, args.cargo, destino)
    except ElectionError:
        print("Não foi possível apresentar os relatórios.", file=sys.stderr)
        return EXIT_FAILURE
    print(_message(report))
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


def _message(report: PresentedReport) -> str:
    lines = [f"Relatórios apresentados: {report.caminho.resolve()}"]
    lines.extend(_summary(grade) for grade in report.grades)
    if not report.aberto:
        lines.append("Não foi possível abrir o navegador.")
    return "\n".join(lines)


def _summary(grade: GradeDePoder) -> str:
    places = _count(len(grade.linhas), "lugar", "lugares")
    parties = _count(len(grade.colunas), "partido", "partidos")
    return f"{_LABELS[grade.nivel]}: {places}, {parties}."


def _count(amount: int, singular: str, plural: str) -> str:
    word = singular if amount == 1 else plural
    return f"{amount} {word}"
