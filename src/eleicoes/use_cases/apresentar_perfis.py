"""Present municipal profiles from stored cells. The script only calls main."""

import argparse
import os
import sys
import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from eleicoes.adapters.html_perfis import html_perfis
from eleicoes.domain.errors import (
    ElectionError,
    InvalidCargoError,
    InvalidElectionYearError,
    InvalidTurnoError,
)
from eleicoes.domain.percentual import format_decimal
from eleicoes.domain.perfis import (
    ProfileReport,
    assemble_profile,
    dataset_from_lines,
    parse_group_span,
    require_profile_cargo,
)
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.ports.perfis import ProfileClusterer, ProfileSource

Render = Callable[[ProfileReport], str]
OpenReport = Callable[[Path], bool]


@dataclass(frozen=True, slots=True)
class PresentedProfile:
    path: Path
    report: ProfileReport
    opened: bool


def build_profile(
    reader: ProfileSource,
    clusterer: ProfileClusterer,
    ano: int,
    turno: int,
    cargo: str,
    grupos: str,
) -> ProfileReport:
    checked = require_profile_cargo(cargo)
    span = parse_group_span(grupos)
    ElectionYear(ano)
    Turno(turno)
    dataset = dataset_from_lines(checked, reader.profile_lines(ano, turno, checked))
    fit = clusterer.fit(dataset.matrix(), span)
    return assemble_profile(
        ano,
        turno,
        dataset,
        fit.assignments,
        fit.centers,
        searched=span.searched,
        silhouette=fit.silhouette,
    )


class PresentProfiles:
    def __init__(
        self,
        reader: ProfileSource,
        clusterer: ProfileClusterer,
        render: Render,
        open_report: OpenReport,
    ) -> None:
        self._reader = reader
        self._clusterer = clusterer
        self._render = render
        self._open = open_report

    def execute(
        self,
        ano: int,
        turno: int,
        cargo: str,
        grupos: str,
        destino: Path,
    ) -> PresentedProfile:
        report = build_profile(self._reader, self._clusterer, ano, turno, cargo, grupos)
        opened = _write(destino, self._render(report), self._open)
        return PresentedProfile(destino, report, opened)


def main(
    argv: Sequence[str] | None = None,
    *,
    reader: ProfileSource | None = None,
    clusterer: ProfileClusterer | None = None,
    render: Render | None = None,
    open_report: OpenReport | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        text = _present(args, reader, clusterer, render, open_report)
    except ElectionError as error:
        print(_failure(error), file=sys.stderr)
        return EXIT_FAILURE
    print(text)
    return EXIT_SUCCESS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agrupa os municípios pelo perfil de voto.")
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--turno", type=int, default=1)
    parser.add_argument("--cargo", default="presidente")
    parser.add_argument("--grupos", default="2-6")
    parser.add_argument("--destino")
    parser.add_argument("--sem-navegador", action="store_true")
    return parser


def _present(
    args: argparse.Namespace,
    reader: ProfileSource | None,
    clusterer: ProfileClusterer | None,
    render: Render | None,
    open_report: OpenReport | None,
) -> str:
    source = reader if reader is not None else _production_reader()
    try:
        presented = PresentProfiles(
            source,
            clusterer if clusterer is not None else _production_clusterer(),
            render if render is not None else html_perfis,
            _choose_opener(args, open_report),
        ).execute(args.ano, args.turno, args.cargo, args.grupos, _destino(args))
    finally:
        source.close()
    return _message(presented)


def _production_reader() -> ProfileSource:
    from eleicoes.adapters.orm.sessions import open_sync_session
    from eleicoes.adapters.postgres_perfis import PostgresStoredLines
    from eleicoes.composition.correspondencia import _host_settings

    settings = _host_settings(_environment())
    return PostgresStoredLines(lambda: open_sync_session(settings))


def _production_clusterer() -> ProfileClusterer:
    from eleicoes.adapters.sklearn_ajuste import SklearnProfileClusterer

    return SklearnProfileClusterer()


def _environment() -> Mapping[str, str]:
    load_dotenv()
    return os.environ


def _destino(args: argparse.Namespace) -> Path:
    if args.destino:
        return Path(args.destino)
    name = f"perfis-{args.cargo}-{args.ano}-turno-{args.turno}.html"
    return Path("relatorios") / name


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


def _message(presented: PresentedProfile) -> str:
    lines = [
        f"Relatório apresentado: {presented.path.resolve()}",
        _summary(presented.report),
    ]
    if not presented.opened:
        lines.append("Não foi possível abrir o navegador.")
    return "\n".join(lines)


def _summary(report: ProfileReport) -> str:
    sizes = ", ".join(str(group.municipios) for group in report.groups)
    text = f"{report.k} grupos. Municípios por grupo: {sizes}."
    if report.searched and report.silhouette is not None:
        return f"Silhueta {format_decimal(report.silhouette)}. {text}"
    return f"Grupos escolhidos. {text}"


def _failure(error: ElectionError) -> str:
    if isinstance(error, InvalidCargoError):
        return "Cargo inválido."
    if isinstance(error, InvalidElectionYearError):
        return "Ano inválido. Informe um ano entre 1994 e 2100."
    if isinstance(error, InvalidTurnoError):
        return "Turno inválido. Informe 1 ou 2."
    return str(error)
