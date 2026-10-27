"""Present "Como votou cada estado" from the stored municipal president votes.

Only reads: the stored places, the party marks and the urn download index.
"""

import argparse
import sys
import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from eleicoes.adapters.arquivo_atomico import gravar_texto
from eleicoes.adapters.html_votos_por_estado import html_dos_estados
from eleicoes.adapters.indice_urnas_secoes import (
    UrnaIndexMismatchError,
    UrnaIndexMissingError,
    contar_secoes,
)
from eleicoes.domain.errors import SCHEMA_OUTDATED_HINT, ElectionError, SchemaOutdatedError
from eleicoes.domain.mapa import Marca, MarkMissingError, MeshMissingError
from eleicoes.domain.mapa_turnos import FinalistsMissingError
from eleicoes.domain.percentual import format_integer, format_percent
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.domain.votos_por_estado import (
    ContagemIndice,
    StatesMissingError,
    VotosPorEstado,
    cobertura_do_turno,
    votos_por_estado,
)
from eleicoes.ports.relatorio_presidente_governador import RelatorioPresidenteGovernadorStore

Render = Callable[[VotosPorEstado, Mapping[int, Marca], datetime, datetime], str]
LoadMarks = Callable[[], Mapping[int, Marca]]
CountSections = Callable[[int], ContagemIndice]
OpenReport = Callable[[Path], bool]
Clock = Callable[[], datetime]
_MESH_DIR: Final = Path("downloads/malha")
_SEGUNDO_TURNO: Final = 2


@dataclass(frozen=True, slots=True)
class PresentedStates:
    destino: Path
    opened: bool
    votos: VotosPorEstado


class PresentStates:
    def __init__(
        self,
        store: RelatorioPresidenteGovernadorStore,
        load_marks: LoadMarks,
        count_sections: CountSections,
        open_report: OpenReport,
        *,
        render: Render = html_dos_estados,
        clock: Clock | None = None,
    ) -> None:
        self._store = store
        self._marks = load_marks
        self._count = count_sections
        self._open = open_report
        self._render = render
        self._clock = clock if clock is not None else _now

    def execute(self, ano: int, turno: int, destino: Path) -> PresentedStates:
        year = ElectionYear(ano).value
        round_ = Turno(turno).value
        stored = self._store.load(year, round_)
        if stored is None or not stored.places:
            raise StatesMissingError(year, round_)
        marcas = self._marks()
        cobertura = cobertura_do_turno(self._count(year), round_)
        votos = votos_por_estado(year, round_, stored.places, cobertura)
        html = self._render(votos, marcas, self._clock(), stored.gerado_em)
        destino.parent.mkdir(parents=True, exist_ok=True)
        gravar_texto(destino, html)
        return PresentedStates(destino, self._open(destino), votos)


def main(
    argv: Sequence[str] | None = None,
    *,
    store: RelatorioPresidenteGovernadorStore | None = None,
    load_marks: LoadMarks | None = None,
    count_sections: CountSections | None = None,
    open_report: OpenReport | None = None,
    clock: Clock | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        report = _present(args, store, load_marks, count_sections, open_report, clock)
    except StatesMissingError as error:
        print(
            f"Não há votos de presidente gravados para o {error.turno}º turno de {error.ano}.",
            file=sys.stderr,
        )
        return EXIT_FAILURE
    except FinalistsMissingError:
        print("Os votos gravados não têm dois candidatos.", file=sys.stderr)
        return EXIT_FAILURE
    except UrnaIndexMissingError as error:
        print(f"Falta {error.caminho}.", file=sys.stderr)
        return EXIT_FAILURE
    except UrnaIndexMismatchError as error:
        print(f"O cabeçalho de {error.caminho} não é o do índice de urnas.", file=sys.stderr)
        return EXIT_FAILURE
    except MeshMissingError as error:
        print(f"Falta {error.nome}.", file=sys.stderr)
        return EXIT_FAILURE
    except MarkMissingError as error:
        for numero in error.partidos:
            print(f"Falta a cor ou a logomarca do partido {numero}.", file=sys.stderr)
        return EXIT_FAILURE
    except SchemaOutdatedError:
        print(SCHEMA_OUTDATED_HINT, file=sys.stderr)
        return EXIT_FAILURE
    except ElectionError:
        print("Não foi possível apresentar como votou cada estado.", file=sys.stderr)
        return EXIT_FAILURE
    _print_success(report)
    return EXIT_SUCCESS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mostra como cada estado votou nos dois mais votados para presidente.",
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--turno", type=int, default=_SEGUNDO_TURNO)
    parser.add_argument("--destino")
    parser.add_argument("--sem-navegador", action="store_true")
    return parser


def _present(
    args: argparse.Namespace,
    store: RelatorioPresidenteGovernadorStore | None,
    load_marks: LoadMarks | None,
    count_sections: CountSections | None,
    open_report: OpenReport | None,
    clock: Clock | None,
) -> PresentedStates:
    cache = store if store is not None else _production_store()
    try:
        return PresentStates(
            cache,
            load_marks if load_marks is not None else _production_marks,
            count_sections if count_sections is not None else _production_count,
            _choose_opener(args, open_report),
            clock=clock,
        ).execute(int(args.ano), int(args.turno), _destino(args))
    finally:
        cache.close()


def _destino(args: argparse.Namespace) -> Path:
    if args.destino:
        return Path(str(args.destino))
    return Path("relatorios") / f"estados-{args.ano}-turno-{args.turno}.html"


def _choose_opener(args: argparse.Namespace, open_report: OpenReport | None) -> OpenReport:
    if open_report is not None:
        return open_report
    if args.sem_navegador:
        return _skip_browser
    return _open_browser


def _production_store() -> RelatorioPresidenteGovernadorStore:
    from eleicoes.composition.presidente_governador import build_cross_report_store

    return build_cross_report_store()


def _production_marks() -> Mapping[int, Marca]:
    from eleicoes.adapters.malha_local import LocalMeshAssets

    return LocalMeshAssets(_MESH_DIR).load_marks()


def _production_count(ano: int) -> ContagemIndice:
    return contar_secoes(Path("downloads") / str(ano) / "indice-urnas.csv")


def _now() -> datetime:
    return datetime.now(UTC)


def _open_browser(path: Path) -> bool:
    return webbrowser.open(path.resolve().as_uri())


def _skip_browser(_path: Path) -> bool:
    return True


def _print_success(report: PresentedStates) -> None:
    votos = report.votos
    brasil = votos.brasil
    print(f"Estados gravados em {report.destino}.")
    print(
        f"{votos.a} venceu em {votos.vitorias_a} estados; {votos.b}, em {votos.vitorias_b}."
        f" Brasil: {votos.a} {format_percent(brasil.fatia_a)} × {votos.b}"
        f" {format_percent(brasil.fatia_b)}, diferença de {format_integer(brasil.diferenca)}"
        " votos."
    )
    total = votos.cobertura.total
    fatia = total.fatia
    if fatia is None or total.esperadas is None:
        print(f"Urnas com boletim: {format_integer(total.com_boletim)}; esperadas: desconhecidas.")
    else:
        print(
            f"Urnas com boletim: {format_integer(total.com_boletim)} de"
            f" {format_integer(total.esperadas)} ({format_percent(fatia)})."
        )
    if votos.faltando:
        print(f"Ainda sem {votos.turno}º turno: {', '.join(votos.faltando)}.")
