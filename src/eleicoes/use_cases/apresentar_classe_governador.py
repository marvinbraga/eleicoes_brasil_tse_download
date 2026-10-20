"""Present the governor class learned from the presidential mix."""

import argparse
import os
import sys
import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from eleicoes.adapters.html_classe_governador import html_classe_governador
from eleicoes.domain.classe_governador import ClassReport, class_report, prepare_class_dataset
from eleicoes.domain.errors import ElectionError, InvalidElectionYearError, InvalidTurnoError
from eleicoes.domain.percentual import format_percent
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.ports.classe_governador import ClassSource, GovernorClassModel

Render = Callable[[ClassReport], str]
OpenReport = Callable[[Path], bool]


@dataclass(frozen=True, slots=True)
class PresentedClass:
    path: Path
    report: ClassReport
    opened: bool


def build_governor_class(
    reader: ClassSource,
    model: GovernorClassModel,
    ano: int,
    turno: int,
) -> ClassReport:
    ElectionYear(ano)
    Turno(turno)
    dataset = prepare_class_dataset(
        reader.class_lines(ano, turno),
        reader.municipal_ufs(ano, turno),
    )
    fit = model.fit(dataset.matrix(), dataset.labels(), dataset.parties, dataset.groups())
    return class_report(ano, turno, dataset, fit.predicted, fit.rules)


class PresentGovernorClass:
    def __init__(
        self,
        reader: ClassSource,
        model: GovernorClassModel,
        render: Render,
        open_report: OpenReport,
    ) -> None:
        self._reader = reader
        self._model = model
        self._render = render
        self._open = open_report

    def execute(self, ano: int, turno: int, destino: Path) -> PresentedClass:
        report = build_governor_class(self._reader, self._model, ano, turno)
        opened = _write(destino, self._render(report), self._open)
        return PresentedClass(destino, report, opened)


def main(
    argv: Sequence[str] | None = None,
    *,
    reader: ClassSource | None = None,
    model: GovernorClassModel | None = None,
    render: Render | None = None,
    open_report: OpenReport | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        text = _present(args, reader, model, render, open_report)
    except ElectionError as error:
        print(_failure(error), file=sys.stderr)
        return EXIT_FAILURE
    print(text)
    return EXIT_SUCCESS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estima a classe do governador a partir do perfil do presidente.",
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--turno", type=int, default=1)
    parser.add_argument("--destino")
    parser.add_argument("--sem-navegador", action="store_true")
    return parser


def _present(
    args: argparse.Namespace,
    reader: ClassSource | None,
    model: GovernorClassModel | None,
    render: Render | None,
    open_report: OpenReport | None,
) -> str:
    source = reader if reader is not None else _production_reader()
    try:
        presented = PresentGovernorClass(
            source,
            model if model is not None else _production_model(),
            render if render is not None else html_classe_governador,
            _choose_opener(args, open_report),
        ).execute(args.ano, args.turno, _destino(args))
    finally:
        source.close()
    return _message(presented)


def _production_reader() -> ClassSource:
    from eleicoes.adapters.orm.sessions import open_sync_session
    from eleicoes.adapters.postgres_perfis import PostgresStoredLines
    from eleicoes.composition.correspondencia import _host_settings

    settings = _host_settings(_environment())
    return PostgresStoredLines(lambda: open_sync_session(settings))


def _production_model() -> GovernorClassModel:
    from eleicoes.adapters.sklearn_ajuste import SklearnGovernorTree

    return SklearnGovernorTree()


def _environment() -> Mapping[str, str]:
    load_dotenv()
    return os.environ


def _destino(args: argparse.Namespace) -> Path:
    if args.destino:
        return Path(args.destino)
    return Path("relatorios") / f"classe-governador-{args.ano}-turno-{args.turno}.html"


def _choose_opener(args: argparse.Namespace, open_report: OpenReport | None) -> OpenReport:
    if open_report is not None:
        return open_report
    if args.sem_navegador:
        return _skip_browser
    return _open_browser


def _write(destino: Path, html: str, open_report: OpenReport) -> bool:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    return open_report(destino)


def _open_browser(path: Path) -> bool:
    return webbrowser.open(path.resolve().as_uri())


def _skip_browser(_path: Path) -> bool:
    return True


def _message(presented: PresentedClass) -> str:
    hit = format_percent(presented.report.hit_rate)
    base = format_percent(presented.report.baseline)
    lider = format_percent(presented.report.leader_baseline)
    lines = [
        f"Relatório apresentado: {presented.path.resolve()}",
        f"Acerto em UF não vista: {hit}. Linha de base da maioria: {base}. "
        f"Linha de base do líder presidencial: {lider}.",
    ]
    if not presented.opened:
        lines.append("Não foi possível abrir o navegador.")
    return "\n".join(lines)


def _failure(error: ElectionError) -> str:
    if isinstance(error, InvalidElectionYearError):
        return "Ano inválido. Informe um ano entre 1994 e 2100."
    if isinstance(error, InvalidTurnoError):
        return "Turno inválido. Informe 1 ou 2."
    return str(error)
