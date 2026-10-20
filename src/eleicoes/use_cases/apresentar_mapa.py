"""Present the president or governor choropleth from stored municipal votes."""

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

from eleicoes.adapters.html_mapa import html_do_mapa
from eleicoes.domain.errors import ElectionError, InvalidStoredReportError
from eleicoes.domain.mapa import (
    BridgeMissingError,
    MarkMissingError,
    MeshMismatchError,
    MeshMissingError,
    PaginaDoMapa,
    RecortePintado,
    recorte_pintado,
)
from eleicoes.domain.presidente_governador import (
    CrossReportView,
    MunicipalPlace,
    view_from_places,
)
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.ports.boletim_consulta import BoletimReader
from eleicoes.ports.grade import MunicipalityNames
from eleicoes.ports.malha import MalhaCarregada, MeshAssets
from eleicoes.ports.relatorio_presidente_governador import (
    RelatorioPresidenteGovernadorStore,
    StoredCrossReport,
)
from eleicoes.use_cases.presidente_governador import collect_places

Collect = Callable[[int, int], tuple[MunicipalPlace, ...]]
Render = Callable[[PaginaDoMapa], str]
OpenReport = Callable[[Path], bool]
_MESH_DIR = Path("downloads/malha")
_EXTERIOR_CSV = Path("dados/exterior.csv")
_VIEWS: Final = ("presidente", "governador")


@dataclass(frozen=True, slots=True)
class PresentedMap:
    destino: Path
    opened: bool
    loaded: bool
    generated_at: datetime

    def __post_init__(self) -> None:
        if self.generated_at.tzinfo is None:
            raise InvalidStoredReportError("gerado_em")


class PresentMap:
    def __init__(
        self,
        collect: Collect,
        store: RelatorioPresidenteGovernadorStore,
        assets: MeshAssets,
        render: Render,
        open_report: OpenReport,
    ) -> None:
        self._collect = collect
        self._store = store
        self._assets = assets
        self._render = render
        self._open = open_report

    def execute(
        self,
        ano: int,
        turno: int,
        cargo: str,
        destino: Path,
        *,
        atualizar: bool = False,
    ) -> PresentedMap:
        _require_scope(ano, turno)
        stored, loaded = self._places(ano, turno, atualizar)
        mesh = self._assets.load()
        _require_country(mesh)
        page = _page(ano, turno, cargo, stored.places, mesh)
        opened = _write(destino, self._render(page), self._open)
        return PresentedMap(destino, opened, loaded, stored.gerado_em)

    def _places(
        self,
        ano: int,
        turno: int,
        atualizar: bool,
    ) -> tuple[StoredCrossReport, bool]:
        if not atualizar:
            stored = self._store.load(ano, turno)
            if stored is not None:
                return stored, True
        places = self._collect(ano, turno)
        moment = self._store.save(ano, turno, places)
        return StoredCrossReport(places, moment), False


def main(
    argv: Sequence[str] | None = None,
    *,
    reader: BoletimReader | None = None,
    names: MunicipalityNames | None = None,
    store: RelatorioPresidenteGovernadorStore | None = None,
    assets: MeshAssets | None = None,
    collect: Collect | None = None,
    render: Render | None = None,
    open_report: OpenReport | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        report = _present(args, reader, names, store, assets, collect, render, open_report)
    except MeshMissingError as error:
        print(f"Falta {error.nome}.", file=sys.stderr)
        return EXIT_FAILURE
    except BridgeMissingError as error:
        _print_bridge(error)
        return EXIT_FAILURE
    except MarkMissingError as error:
        _print_marks(error)
        return EXIT_FAILURE
    except ElectionError:
        print("Não foi possível apresentar o mapa.", file=sys.stderr)
        return EXIT_FAILURE
    _print_success(report)
    return EXIT_SUCCESS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Pinta o partido líder de presidente ou de governador,"
            " ou a classe presidente × governador (cruzamento)."
        ),
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--turno", type=int, default=1)
    parser.add_argument("--cargo", default="")
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
    assets: MeshAssets | None,
    collect: Collect | None,
    render: Render | None,
    open_report: OpenReport | None,
) -> PresentedMap:
    destino = _destino(args)
    cache = store if store is not None else _production_store()
    try:
        return PresentMap(
            _collect_for(reader, names, collect),
            cache,
            assets if assets is not None else _production_assets(),
            render if render is not None else html_do_mapa,
            _choose_opener(args, open_report),
        ).execute(args.ano, args.turno, str(args.cargo), destino, atualizar=bool(args.atualizar))
    finally:
        cache.close()


def _destino(args: argparse.Namespace) -> Path:
    if args.destino:
        return Path(str(args.destino))
    name = f"mapa-{args.cargo}-{args.ano}-turno-{args.turno}.html"
    return Path("relatorios") / name


def _collect_for(
    reader: BoletimReader | None,
    names: MunicipalityNames | None,
    collect: Collect | None,
) -> Collect:
    if collect is not None:
        return collect
    if reader is None or names is None:
        return _production_collect
    return _bound_collect(reader, names)


def _bound_collect(reader: BoletimReader, names: MunicipalityNames) -> Collect:
    def collect(ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
        return collect_places(reader, names, ano, turno)

    return collect


def _choose_opener(args: argparse.Namespace, open_report: OpenReport | None) -> OpenReport:
    if open_report is not None:
        return open_report
    if args.sem_navegador:
        return _skip_browser
    return _open_browser


def _production_store() -> RelatorioPresidenteGovernadorStore:
    from eleicoes.composition.presidente_governador import build_cross_report_store

    return build_cross_report_store()


def _production_assets() -> MeshAssets:
    from eleicoes.adapters.malha_local import LocalMeshAssets

    return LocalMeshAssets(_MESH_DIR, _EXTERIOR_CSV)


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


def _require_scope(ano: int, turno: int) -> None:
    ElectionYear(ano)
    Turno(turno)


def _require_country(mesh: MalhaCarregada) -> None:
    if mesh.manifesto.brasil_id not in mesh.ids_pais:
        raise MeshMismatchError("brasil_id")


def _page(
    ano: int,
    turno: int,
    cargo: str,
    places: tuple[MunicipalPlace, ...],
    mesh: MalhaCarregada,
) -> PaginaDoMapa:
    manifesto = mesh.manifesto
    view = view_from_places(ano, turno, places)
    painted = _paint(view, cargo, mesh)
    return PaginaDoMapa(
        ano,
        turno,
        cargo,
        painted,
        mesh.municipios,
        mesh.ufs,
        mesh.paises,
        manifesto.municipios_objeto,
        manifesto.ufs_objeto,
        manifesto.paises_objeto,
        manifesto.brasil_id,
        mesh.ol_js,
        mesh.ol_css,
        mesh.topojson_js,
        _views(view, cargo, painted, mesh),
    )


def _paint(view: CrossReportView, cargo: str, mesh: MalhaCarregada) -> RecortePintado:
    return recorte_pintado(
        view,
        cargo,
        mesh.ponte,
        mesh.marcas,
        mesh.codigos_municipio,
        mesh.codigos_uf,
        mesh.manifesto.brasil_id,
        exterior=mesh.exterior,
    )


def _views(
    view: CrossReportView,
    cargo: str,
    painted: RecortePintado,
    mesh: MalhaCarregada,
) -> dict[str, RecortePintado]:
    recortes: dict[str, RecortePintado] = {}
    for other in _VIEWS:
        if other == cargo:
            recortes[other] = painted
            continue
        try:
            recortes[other] = _paint(view, other, mesh)
        except MarkMissingError:
            continue
    return recortes


def _write(destino: Path, html: str, open_report: OpenReport) -> bool:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    return open_report(destino)


def _open_browser(path: Path) -> bool:
    return webbrowser.open(path.resolve().as_uri())


def _skip_browser(_path: Path) -> bool:
    return True


def _print_success(report: PresentedMap) -> None:
    print(f"Mapa gravado em {report.destino}.")
    if report.loaded:
        print(_loaded_line(report.generated_at))
    else:
        print("Votos gravados no banco.")


def _loaded_line(moment: datetime) -> str:
    stamp = moment.astimezone().strftime("%Y-%m-%d %H:%M")
    return f"Votos carregados do banco, gerados em {stamp}."


def _print_bridge(error: BridgeMissingError) -> None:
    for uf, codigo in error.ausentes:
        print(
            f"Não há código IBGE para o município {codigo} ({uf}).",
            file=sys.stderr,
        )


def _print_marks(error: MarkMissingError) -> None:
    for numero in error.partidos:
        print(f"Falta a cor ou a logomarca do partido {numero}.", file=sys.stderr)
