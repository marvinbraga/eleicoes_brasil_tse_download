"""Present the president or governor choropleth from stored municipal votes."""

import argparse
import json
import os
import sys
import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

from eleicoes.adapters.html_mapa import html_do_mapa
from eleicoes.domain.errors import (
    SCHEMA_OUTDATED_HINT,
    ElectionError,
    InvalidStoredReportError,
    SchemaOutdatedError,
)
from eleicoes.domain.mapa import (
    BridgeMissingError,
    MarkMissingError,
    MeshMismatchError,
    MeshMissingError,
    PaginaDoMapa,
    RecortePintado,
    recorte_pintado,
)
from eleicoes.domain.mapa_turnos import (
    GOVERNADOR,
    ComparativoTurnos,
    FinalistsMissingError,
    chave_tse,
    comparar_turnos,
    finalistas,
    finalistas_de_governador,
)
from eleicoes.domain.presidente_governador import (
    CrossReportView,
    MunicipalPlace,
    view_from_places,
)
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.transferencia import (
    estimar_por_uf,
    grupos_do_primeiro,
    observacoes,
    parte_estimada_de_a,
)
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
Present = Callable[[int, int], tuple[str, ...]]
LastLoad = Callable[[int, int], datetime | None]
# (ano, turno, UFs) → {(UF, código TSE de cinco dígitos): (aptos, comparecimento)} de presidente.
Participation = Callable[[int, int, tuple[str, ...]], Mapping[tuple[str, str], tuple[int, int]]]
Render = Callable[[PaginaDoMapa], str]
OpenReport = Callable[[Path], bool]
_MESH_DIR = Path("downloads/malha")
_EXTERIOR_CSV = Path("dados/exterior.csv")
_CALIBRACAO = Path("dados/calibracao_turnos_2022.json")
_VIEWS: Final = ("presidente", "governador")
_PRIMEIRO_TURNO: Final = 1
_SEGUNDO_TURNO: Final = 2
_APOIADO: Final = 22
_PRESIDENTE: Final = "presidente"
_MUNICIPIO: Final = "municipio"


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
        present: Present | None = None,
        apoiado: int | None = _APOIADO,
        last_load: LastLoad | None = None,
        participation: Participation | None = None,
        calibracao: Mapping[str, object] | None = None,
    ) -> None:
        self._collect = collect
        self._store = store
        self._assets = assets
        self._render = render
        self._open = open_report
        self._present = present
        self._apoiado = apoiado
        self._last_load = last_load
        self._participation = participation
        self._calibracao = calibracao

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
        segundo = self._second_round(ano, turno, atualizar)
        mesh = self._assets.load()
        _require_country(mesh)
        page = _page(ano, turno, cargo, stored.places, mesh)
        if segundo:
            participacao = self._turnout(ano, segundo)
            page = replace(
                page,
                turnos=_turnos(stored.places, segundo, mesh, self._apoiado, participacao),
                calibracao=self._calibracao,
                turnos_governador=_turnos_de_governador(stored.places, segundo, mesh),
            )
        opened = _write(destino, self._render(page), self._open)
        return PresentedMap(destino, opened, loaded, stored.gerado_em)

    def _places(
        self,
        ano: int,
        turno: int,
        atualizar: bool,
    ) -> tuple[StoredCrossReport, bool]:
        if turno == _SEGUNDO_TURNO and self._present is not None:
            return self._checked_second_round(ano, atualizar)
        if not atualizar:
            stored = self._store.load(ano, turno)
            if stored is not None:
                return stored, True
        places = self._collect(ano, turno)
        moment = self._store.save(ano, turno, places)
        return StoredCrossReport(places, moment), False

    def _second_round(self, ano: int, turno: int, atualizar: bool) -> tuple[MunicipalPlace, ...]:
        """O 2º turno ainda chega por UF: o gravado só vale se cobrir as mesmas UFs do banco
        e se nenhuma UF foi importada de novo depois que ele foi gravado."""
        if turno != _PRIMEIRO_TURNO or self._present is None:
            return ()
        if not self._present(ano, _SEGUNDO_TURNO):
            return ()
        return self._checked_second_round(ano, atualizar)[0].places

    def _checked_second_round(self, ano: int, atualizar: bool) -> tuple[StoredCrossReport, bool]:
        """O 2º turno gravado, se ainda vale; senão, recolhido e gravado de novo."""
        ufs = frozenset(self._present(ano, _SEGUNDO_TURNO)) if self._present else frozenset()
        stored = None if atualizar else self._store.load(ano, _SEGUNDO_TURNO)
        if stored is not None and self._still_valid(ano, stored, ufs):
            return stored, True
        places = self._collect(ano, _SEGUNDO_TURNO)
        moment = self._store.save(ano, _SEGUNDO_TURNO, places)
        return StoredCrossReport(places, moment), False

    def _turnout(
        self, ano: int, segundo: tuple[MunicipalPlace, ...]
    ) -> dict[tuple[int, str, str], tuple[int, int]]:
        if self._participation is None:
            return {}
        ufs = tuple(sorted({place.uf for place in segundo}))
        found: dict[tuple[int, str, str], tuple[int, int]] = {}
        for turno in (_PRIMEIRO_TURNO, _SEGUNDO_TURNO):
            for (uf, codigo), lida in self._participation(ano, turno, ufs).items():
                found[(turno, uf, codigo)] = lida
        return found

    def _still_valid(self, ano: int, stored: StoredCrossReport, ufs: frozenset[str]) -> bool:
        if frozenset(place.uf for place in stored.places) != ufs:
            return False
        if self._last_load is None:
            return True
        # Sem marca de carga (UFs importadas antes dela existir) vale só a checagem das UFs.
        carga = self._last_load(ano, _SEGUNDO_TURNO)
        return carga is None or carga < stored.gerado_em


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
    present: Present | None = None,
    last_load: LastLoad | None = None,
    participation: Participation | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        report = _present(
            args,
            reader,
            names,
            store,
            assets,
            collect,
            render,
            open_report,
            (present, last_load, participation),
        )
    except MeshMissingError as error:
        print(f"Falta {error.nome}.", file=sys.stderr)
        return EXIT_FAILURE
    except BridgeMissingError as error:
        _print_bridge(error)
        return EXIT_FAILURE
    except MarkMissingError as error:
        _print_marks(error)
        return EXIT_FAILURE
    except SchemaOutdatedError:
        print(SCHEMA_OUTDATED_HINT, file=sys.stderr)
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
    parser.add_argument(
        "--apoiado",
        type=int,
        default=_APOIADO,
        help=(
            "Finalista que os eliminados apoiaram no 2º turno."
            f" Ordena os cenários do comparativo. Padrão: {_APOIADO}."
        ),
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
    rounds: tuple[Present | None, LastLoad | None, Participation | None],
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
            _present_for(reader, collect, rounds[0]),
            int(args.apoiado),
            _last_load_for(reader, collect, rounds[1]),
            _participation_for(reader, collect, rounds[2]),
            ler_calibracao(_CALIBRACAO),
        ).execute(args.ano, args.turno, str(args.cargo), destino, atualizar=bool(args.atualizar))
    finally:
        cache.close()


def ler_calibracao(caminho: Path) -> dict[str, object] | None:
    """Resumo de 2022 para a legenda: parte dos municípios marcada em cada cenário."""
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        cenarios = dados["cenarios"]
        return {
            "ano": int(dados["eleicao"]["ano"]),
            "lugares": int(cenarios[0]["municipios"]["com_base"]),
            "normal": float(dados["referencia_normal"]["fora"]),
            "fora": {item["chave"]: float(item["municipios"]["fracao_fora"]) for item in cenarios},
            "moderado": {
                item["chave"]: float(item["municipios"]["fracao_acima_do_moderado"])
                for item in cenarios
            },
        }
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None


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


def _present_for(
    reader: BoletimReader | None,
    collect: Collect | None,
    present: Present | None,
) -> Present | None:
    if present is not None:
        return present
    if reader is not None:
        return _bound_present(reader)
    if collect is not None:
        return None
    return _production_present


def _bound_present(reader: BoletimReader) -> Present:
    def present(ano: int, turno: int) -> tuple[str, ...]:
        return reader.present_ufs(ano, turno, _PRESIDENTE)

    return present


def _last_load_for(
    reader: BoletimReader | None,
    collect: Collect | None,
    last_load: LastLoad | None,
) -> LastLoad | None:
    if last_load is not None:
        return last_load
    if reader is not None:
        return _bound_last_load(reader)
    if collect is not None:
        return None
    return _production_last_load


def _bound_last_load(reader: BoletimReader) -> LastLoad:
    def last_load(ano: int, turno: int) -> datetime | None:
        return reader.last_load(ano, turno)

    return last_load


def _participation_for(
    reader: BoletimReader | None,
    collect: Collect | None,
    participation: Participation | None,
) -> Participation | None:
    if participation is not None:
        return participation
    if reader is not None:
        return _bound_participation(reader)
    if collect is not None:
        return None
    return _production_participation


def _bound_participation(reader: BoletimReader) -> Participation:
    def participation(
        ano: int, turno: int, ufs: tuple[str, ...]
    ) -> dict[tuple[str, str], tuple[int, int]]:
        found: dict[tuple[str, str], tuple[int, int]] = {}
        for uf in ufs:
            for linha in reader.participation(ano, turno, uf, _PRESIDENTE, _MUNICIPIO):
                chave = (uf, chave_tse(str(linha.municipio)))
                found[chave] = (linha.eleitores_aptos, linha.comparecimento)
        return found

    return participation


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


def _production_present(ano: int, turno: int) -> tuple[str, ...]:
    from eleicoes.composition.boletim import build_boletim_reader

    reader = build_boletim_reader(_environment())
    try:
        return reader.present_ufs(ano, turno, _PRESIDENTE)
    finally:
        reader.close()


def _production_last_load(ano: int, turno: int) -> datetime | None:
    from eleicoes.composition.boletim import build_boletim_reader

    reader = build_boletim_reader(_environment())
    try:
        return reader.last_load(ano, turno)
    finally:
        reader.close()


def _production_participation(
    ano: int, turno: int, ufs: tuple[str, ...]
) -> Mapping[tuple[str, str], tuple[int, int]]:
    from eleicoes.composition.boletim import build_boletim_reader

    reader = build_boletim_reader(_environment())
    try:
        return _bound_participation(reader)(ano, turno, ufs)
    finally:
        reader.close()


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


def _turnos(
    primeiro: tuple[MunicipalPlace, ...],
    segundo: tuple[MunicipalPlace, ...],
    mesh: MalhaCarregada,
    apoiado: int | None,
    participacao: Mapping[tuple[int, str, str], tuple[int, int]],
) -> ComparativoTurnos:
    partes, pequenas = _partes_estimadas(primeiro, segundo, apoiado)
    return comparar_turnos(
        primeiro,
        segundo,
        mesh.ponte,
        mesh.codigos_municipio,
        mesh.codigos_uf,
        mesh.manifesto.brasil_id,
        exterior=mesh.exterior,
        apoiado=apoiado,
        participacao=participacao,
        partes_estimadas=partes,
        amostras_pequenas=pequenas,
    )


def _partes_estimadas(
    primeiro: tuple[MunicipalPlace, ...],
    segundo: tuple[MunicipalPlace, ...],
    apoiado: int | None,
) -> tuple[dict[str, Fraction], frozenset[str]]:
    """Parte de A por UF, da regressão ecológica, e as UFs de amostra pequena.

    Sem reamostras: o mapa só usa o ponto."""
    try:
        a, b = finalistas(segundo, apoiado)
    except FinalistsMissingError:
        return {}, frozenset()
    grupos = grupos_do_primeiro(primeiro, a, b)
    estimadas, _ = estimar_por_uf(observacoes(primeiro, segundo, grupos), grupos, reamostras=0)
    partes = {estimativa.uf: parte_estimada_de_a(estimativa) for estimativa in estimadas}
    return partes, frozenset(item.uf for item in estimadas if item.amostra_pequena)


def _turnos_de_governador(
    primeiro: tuple[MunicipalPlace, ...],
    segundo: tuple[MunicipalPlace, ...],
    mesh: MalhaCarregada,
) -> ComparativoTurnos | None:
    """Só existe quando alguma UF importada tem 2º turno de governador."""
    if not finalistas_de_governador(primeiro, segundo):
        return None
    return comparar_turnos(
        primeiro,
        segundo,
        mesh.ponte,
        mesh.codigos_municipio,
        mesh.codigos_uf,
        mesh.manifesto.brasil_id,
        cargo=GOVERNADOR,
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
