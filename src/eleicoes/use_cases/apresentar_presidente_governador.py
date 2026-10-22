"""Present the president × governor HTML from stored municipal cells."""

import argparse
import os
import sys
import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

from eleicoes.adapters.html_presidente_governador import html_presidente_governador
from eleicoes.domain.errors import ElectionError, InvalidStoredReportError
from eleicoes.domain.presidente_governador import CrossReportView, MunicipalPlace, view_from_places
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear, Turno, Uf
from eleicoes.ports.boletim_consulta import BoletimReader
from eleicoes.ports.grade import MunicipalityNames
from eleicoes.ports.relatorio_presidente_governador import (
    RelatorioPresidenteGovernadorStore,
    StoredCrossReport,
)
from eleicoes.use_cases.failure import failure_line
from eleicoes.use_cases.presidente_governador import collect_places

Collect = Callable[[int, int], tuple[MunicipalPlace, ...]]
Render = Callable[[CrossReportView], str]
OpenReport = Callable[[Path], bool]

_FAILURE: Final = "Não foi possível apresentar os relatórios."


@dataclass(frozen=True, slots=True)
class PresentedCrossReport:
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


class PresentPresidentGovernor:
    def __init__(
        self,
        collect: Collect,
        store: RelatorioPresidenteGovernadorStore,
        render: Render,
        open_report: OpenReport,
    ) -> None:
        self._collect = collect
        self._store = store
        self._render = render
        self._open = open_report

    def execute(
        self,
        ano: int,
        turno: int,
        uf: str,
        destino: Path,
        *,
        atualizar: bool = False,
    ) -> PresentedCrossReport:
        _require_scope(ano, turno, uf)
        if not atualizar:
            stored = self._store.load(ano, turno)
            if stored is not None:
                return self._publish(ano, turno, stored, destino, loaded=True)
        return self._calculate(ano, turno, destino)

    def _calculate(self, ano: int, turno: int, destino: Path) -> PresentedCrossReport:
        places = self._collect(ano, turno)
        moment = self._store.save(ano, turno, places)
        stored = StoredCrossReport(places, moment)
        return self._publish(ano, turno, stored, destino, loaded=False)

    def _publish(
        self,
        ano: int,
        turno: int,
        stored: StoredCrossReport,
        destino: Path,
        *,
        loaded: bool,
    ) -> PresentedCrossReport:
        view = view_from_places(ano, turno, stored.places)
        opened = _write(destino, self._render(view), self._open)
        return PresentedCrossReport(destino, _summary(view), opened, loaded, stored.gerado_em)


def main(
    argv: Sequence[str] | None = None,
    *,
    reader: BoletimReader | None = None,
    names: MunicipalityNames | None = None,
    store: RelatorioPresidenteGovernadorStore | None = None,
    render: Render | None = None,
    open_report: OpenReport | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        text = _present(args, reader, names, store, render, open_report)
    except ElectionError as exc:
        print(failure_line(_FAILURE, exc), file=sys.stderr)
        return EXIT_FAILURE
    print(text)
    return EXIT_SUCCESS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cruza o partido do governador com o 1º e o 2º da presidência.",
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--turno", type=int, default=1)
    parser.add_argument("--uf", default="AC")
    parser.add_argument("--destino")
    parser.add_argument("--sem-navegador", action="store_true")
    parser.add_argument(
        "--atualizar",
        action="store_true",
        help="Relê os boletins e substitui os votos municipais gravados no banco.",
    )
    return parser


def _present(
    args: argparse.Namespace,
    reader: BoletimReader | None,
    names: MunicipalityNames | None,
    store: RelatorioPresidenteGovernadorStore | None,
    render: Render | None,
    open_report: OpenReport | None,
) -> str:
    destino = _destino(args)
    cache = store if store is not None else _production_store()
    try:
        report = PresentPresidentGovernor(
            _collect_for(reader, names),
            cache,
            render if render is not None else html_presidente_governador,
            _choose_opener(args, open_report),
        ).execute(args.ano, args.turno, args.uf, destino, atualizar=bool(args.atualizar))
    finally:
        cache.close()
    return _message(report)


def _destino(args: argparse.Namespace) -> Path:
    if args.destino:
        return Path(args.destino)
    name = f"{args.uf.strip().lower()}-{args.ano}-turno-{args.turno}-presidente-governador.html"
    return Path("relatorios") / name


def _collect_for(reader: BoletimReader | None, names: MunicipalityNames | None) -> Collect:
    if reader is None or names is None:
        return _production_collect
    return lambda ano, turno: collect_places(reader, names, ano, turno)


def _choose_opener(args: argparse.Namespace, open_report: OpenReport | None) -> OpenReport:
    if open_report is not None:
        return open_report
    if args.sem_navegador:
        return _skip_browser
    return _open_browser


def _production_store() -> RelatorioPresidenteGovernadorStore:
    from eleicoes.composition.presidente_governador import build_cross_report_store

    return build_cross_report_store()


def _production_collect(ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
    from eleicoes.composition.boletim import build_boletim_reader
    from eleicoes.composition.grade import build_municipality_names

    env = _environment()
    reader = build_boletim_reader(env)
    names = build_municipality_names(env)
    try:
        return collect_places(reader, names, ano, turno)
    finally:
        reader.close()
        names.close()


def _environment() -> Mapping[str, str]:
    load_dotenv()
    return os.environ


def _require_scope(ano: int, turno: int, uf: str) -> None:
    ElectionYear(ano)
    Turno(turno)
    Uf(uf)


def _write(destino: Path, html: str, open_report: OpenReport) -> bool:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    return open_report(destino)


def _open_browser(path: Path) -> bool:
    return webbrowser.open(path.resolve().as_uri())


def _skip_browser(_path: Path) -> bool:
    return True


def _message(report: PresentedCrossReport) -> str:
    lines: list[str] = []
    if report.loaded:
        lines.append(_loaded_line(report.generated_at))
    lines.append(f"Relatórios apresentados: {report.path.resolve()}")
    lines.append(report.summary)
    if not report.opened:
        lines.append("Não foi possível abrir o navegador.")
    if not report.loaded:
        lines.append("Relatório gravado no banco.")
    return "\n".join(lines)


def _loaded_line(moment: datetime) -> str:
    stamp = moment.astimezone().strftime("%Y-%m-%d %H:%M")
    return f"Relatório carregado do banco, gerado em {stamp}."


def _summary(view: CrossReportView) -> str:
    municipal = sum(len(rows) for _code, rows in view.municipalities)
    country = 0 if view.country is None else 1
    lines = (
        _count("Composição", _cities(view), "município", "municípios"),
        _count("Por município", municipal, "lugar", "lugares"),
        _count("Por estado", len(view.states), "lugar", "lugares"),
        _count("Por região", len(view.regions), "lugar", "lugares"),
        _count("No país", country, "lugar", "lugares"),
    )
    return "\n".join(lines)


def _cities(view: CrossReportView) -> int:
    return sum(item.cidades for item in view.composition.classes)


def _count(label: str, amount: int, singular: str, plural: str) -> str:
    word = singular if amount == 1 else plural
    return f"{label}: {amount} {word}."
