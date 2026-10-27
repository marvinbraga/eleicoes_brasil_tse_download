"""Present the president first × second round by macro-region and municipality size."""

import argparse
import os
import sys
import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Protocol

from dotenv import load_dotenv

from eleicoes.adapters.arquivo_atomico import gravar_texto
from eleicoes.adapters.html_regioes_porte import html_de_regioes_e_porte
from eleicoes.domain.errors import SCHEMA_OUTDATED_HINT, ElectionError, SchemaOutdatedError
from eleicoes.domain.mapa import Marca, MeshMissingError
from eleicoes.domain.mapa_turnos import FinalistsMissingError, chave_tse
from eleicoes.domain.percentual import format_integer, format_percent
from eleicoes.domain.presidente_governador import MunicipalPlace
from eleicoes.domain.regioes_porte import (
    REFERENCIA,
    LinhaGrupo,
    RegioesEPorte,
    regioes_e_porte,
    ufs_com_os_dois_turnos,
)
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear
from eleicoes.ports.boletim_consulta import BoletimReader
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport

Render = Callable[[int, datetime, RegioesEPorte, Mapping[int, Marca]], str]
Marks = Callable[[], Mapping[int, Marca]]
OpenReport = Callable[[Path], bool]
Clock = Callable[[], datetime]
_PRESIDENTE: Final = "presidente"
_MUNICIPIO: Final = "municipio"
_PRIMEIRO_TURNO: Final = 1
_SEGUNDO_TURNO: Final = 2
_MESH_DIR: Final = Path("downloads/malha")


class StoredRoundMissingError(ElectionError):
    def __init__(self, ano: int, turno: int) -> None:
        self.ano = ano
        self.turno = turno
        super().__init__(f"no stored president places for {ano}, round {turno}")


class StoredPlaces(Protocol):
    def load(self, ano: int, turno: int) -> StoredCrossReport | None: ...


@dataclass(frozen=True, slots=True)
class PresentedRegionsAndSize:
    destino: Path
    opened: bool
    leitura: RegioesEPorte


class PresentRegionsAndSize:
    def __init__(
        self,
        store: StoredPlaces,
        reader: BoletimReader,
        marks: Marks,
        open_report: OpenReport,
        *,
        render: Render = html_de_regioes_e_porte,
        clock: Clock | None = None,
        referencia: int = REFERENCIA,
    ) -> None:
        self._store = store
        self._reader = reader
        self._marks = marks
        self._open = open_report
        self._render = render
        self._clock = clock if clock is not None else _now
        self._referencia = referencia
        self._aptos: dict[tuple[int, str], dict[tuple[str, str], int]] = {}

    def execute(self, ano: int, destino: Path) -> PresentedRegionsAndSize:
        year = ElectionYear(ano).value
        primeiro = self._places(year, _PRIMEIRO_TURNO)
        segundo = self._places(year, _SEGUNDO_TURNO)
        eleitores: dict[tuple[str, str], int] = {}
        for uf in ufs_com_os_dois_turnos(primeiro, segundo):
            eleitores.update(self._eleitores(year, uf))
        leitura = regioes_e_porte(
            year,
            primeiro,
            segundo,
            eleitores,
            referencia=self._referencia,
            ufs_no_boletim=self._reader.present_ufs(year, _SEGUNDO_TURNO, _PRESIDENTE),
        )
        html = self._render(year, self._clock(), leitura, self._marks())
        destino.parent.mkdir(parents=True, exist_ok=True)
        gravar_texto(destino, html)
        return PresentedRegionsAndSize(destino, self._open(destino), leitura)

    def _places(self, ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
        stored = self._store.load(ano, turno)
        if stored is None or not stored.places:
            raise StoredRoundMissingError(ano, turno)
        return stored.places

    def _eleitores(self, ano: int, uf: str) -> dict[tuple[str, str], int]:
        # One turnout query per UF and run; MG alone takes tens of seconds.
        chave = (ano, uf)
        if chave not in self._aptos:
            linhas = self._reader.participation(ano, _PRIMEIRO_TURNO, uf, _PRESIDENTE, _MUNICIPIO)
            self._aptos[chave] = {
                (uf, chave_tse(str(linha.municipio))): linha.eleitores_aptos for linha in linhas
            }
        return self._aptos[chave]


def main(
    argv: Sequence[str] | None = None,
    *,
    store: StoredPlaces | None = None,
    reader: BoletimReader | None = None,
    marks: Marks | None = None,
    open_report: OpenReport | None = None,
    clock: Clock | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        report = _present(args, store, reader, marks, open_report, clock)
    except StoredRoundMissingError as error:
        print(
            f"Não há {error.turno}º turno de presidente gravado para {error.ano}. Rode "
            "scripts/relatorio_presidente_governador.py com --turno "
            f"{error.turno} antes.",
            file=sys.stderr,
        )
        return EXIT_FAILURE
    except FinalistsMissingError:
        print("O 2º turno gravado não tem dois finalistas.", file=sys.stderr)
        return EXIT_FAILURE
    except MeshMissingError as error:
        print(f"Falta {error.nome}.", file=sys.stderr)
        return EXIT_FAILURE
    except SchemaOutdatedError:
        print(SCHEMA_OUTDATED_HINT, file=sys.stderr)
        return EXIT_FAILURE
    except ElectionError:
        print("Não foi possível apresentar as regiões e o porte.", file=sys.stderr)
        return EXIT_FAILURE
    _print_success(report)
    return EXIT_SUCCESS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compara o 1º e o 2º turno de presidente por região e porte do município.",
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--destino")
    parser.add_argument("--sem-navegador", action="store_true")
    return parser


def _present(
    args: argparse.Namespace,
    store: StoredPlaces | None,
    reader: BoletimReader | None,
    marks: Marks | None,
    open_report: OpenReport | None,
    clock: Clock | None,
) -> PresentedRegionsAndSize:
    destino = _destino(args)
    opener = _choose_opener(args, open_report)
    if store is not None and reader is not None:
        marcas = marks if marks is not None else _no_marks
        use_case = PresentRegionsAndSize(store, reader, marcas, opener, clock=clock)
        return use_case.execute(int(args.ano), destino)
    return _production(int(args.ano), destino, opener, clock)


def _production(
    ano: int, destino: Path, opener: OpenReport, clock: Clock | None
) -> PresentedRegionsAndSize:
    from eleicoes.adapters.malha_local import LocalMeshAssets
    from eleicoes.composition.boletim import build_boletim_reader
    from eleicoes.composition.presidente_governador import build_cross_report_store

    env = _environment()
    store = build_cross_report_store(env)
    reader = build_boletim_reader(env)
    marks = LocalMeshAssets(_MESH_DIR).marcas
    try:
        return PresentRegionsAndSize(store, reader, marks, opener, clock=clock).execute(
            ano, destino
        )
    finally:
        reader.close()
        store.close()


def _no_marks() -> Mapping[int, Marca]:
    return {}


def _destino(args: argparse.Namespace) -> Path:
    if args.destino:
        return Path(str(args.destino))
    return Path("relatorios") / f"regioes-porte-{args.ano}.html"


def _choose_opener(args: argparse.Namespace, open_report: OpenReport | None) -> OpenReport:
    if open_report is not None:
        return open_report
    if args.sem_navegador:
        return _skip_browser
    return _open_browser


def _environment() -> Mapping[str, str]:
    load_dotenv()
    return os.environ


def _now() -> datetime:
    return datetime.now(UTC)


def _open_browser(path: Path) -> bool:
    return webbrowser.open(path.resolve().as_uri())


def _skip_browser(_path: Path) -> bool:
    return True


def _print_success(report: PresentedRegionsAndSize) -> None:
    leitura = report.leitura
    print(f"Regiões e porte gravados em {report.destino}.")
    if leitura.sem_segundo_turno:
        print(f"Sem 2º turno no relatório gravado: {', '.join(leitura.sem_segundo_turno)}.")
    if leitura.fora_do_relatorio:
        print(
            "Já com 2º turno nos boletins, mas fora do relatório gravado: "
            f"{', '.join(leitura.fora_do_relatorio)}."
        )
    print(
        f"Municípios pareados: {format_integer(leitura.brasil.municipios)}. "
        f"Só no 1º turno: {format_integer(leitura.so_no_primeiro)}. "
        f"Sem eleitorado: {format_integer(leitura.sem_eleitorado)}."
    )
    for linha in (*leitura.regioes, leitura.brasil, *leitura.portes, leitura.brasil_sem_exterior):
        print(_resumo(linha, leitura.a, leitura.b))


def _resumo(linha: LinhaGrupo, a: int, b: int) -> str:
    return (
        f"{linha.rotulo} ({format_integer(linha.municipios)}): "
        f"{a} {format_percent(linha.segundo.fatia_a)}, "
        f"{b} {format_percent(linha.segundo.fatia_b)}, "
        f"diferença {format_integer(linha.diferenca)}; variação {a} "
        f"{format_integer(linha.variacao_a)}, {b} {format_integer(linha.variacao_b)}; "
        f"virada {'+' if linha.virada > 0 else ''}"
        f"{format_percent(linha.virada).removesuffix('%')} p.p."
    )
