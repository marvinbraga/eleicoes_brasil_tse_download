"""Present where the finalists' new second-round votes came from, per municipality."""

import argparse
import json
import os
import sys
import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

from eleicoes.adapters.arquivo_atomico import gravar_texto
from eleicoes.adapters.csv_origem_votos import csv_da_origem
from eleicoes.adapters.html_origem_votos import PaginaDaOrigem, html_da_origem
from eleicoes.domain.errors import SCHEMA_OUTDATED_HINT, ElectionError, SchemaOutdatedError
from eleicoes.domain.mapa_turnos import FinalistsMissingError, chave_tse
from eleicoes.domain.origem_votos import OrigemDosVotos, analisar_origem
from eleicoes.domain.percentual import format_integer, format_percent
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear
from eleicoes.ports.boletim_consulta import BoletimReader
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport

Load = Callable[[int, int], StoredCrossReport | None]
# (ano, turno, UFs) → {(UF, código TSE de cinco dígitos): (aptos, comparecimento)} de presidente.
Participation = Callable[[int, int, tuple[str, ...]], Mapping[tuple[str, str], tuple[int, int]]]
LastLoad = Callable[[int, int], datetime | None]
Render = Callable[[PaginaDaOrigem], str]
Tabulate = Callable[[OrigemDosVotos], str]
OpenReport = Callable[[Path], bool]
Clock = Callable[[], datetime]
_MARCAS = Path("downloads/malha/marcas.json")
_PRIMEIRO_TURNO: Final = 1
_SEGUNDO_TURNO: Final = 2
_PRESIDENTE: Final = "presidente"
_MUNICIPIO: Final = "municipio"


class StoredRoundMissingError(ElectionError):
    def __init__(self, ano: int, turno: int) -> None:
        self.ano = ano
        self.turno = turno
        super().__init__(f"no stored municipal places for {ano}, round {turno}")


@dataclass(frozen=True, slots=True)
class PresentedOrigin:
    destino: Path
    tabela: Path
    opened: bool
    origem: OrigemDosVotos


class PresentOrigin:
    def __init__(
        self,
        load: Load,
        participation: Participation,
        open_report: OpenReport,
        *,
        last_load: LastLoad | None = None,
        cores: Mapping[int, str] | None = None,
        siglas: Mapping[int, str] | None = None,
        render: Render = html_da_origem,
        tabulate: Tabulate = csv_da_origem,
        clock: Clock | None = None,
    ) -> None:
        self._load = load
        self._participation = participation
        self._open = open_report
        self._last_load = last_load
        self._cores = cores if cores is not None else {}
        self._siglas = siglas if siglas is not None else {}
        self._render = render
        self._tabulate = tabulate
        self._clock = clock if clock is not None else _now

    def execute(self, ano: int, destino: Path) -> PresentedOrigin:
        year = ElectionYear(ano).value
        primeiro = self._stored(year, _PRIMEIRO_TURNO)
        segundo = self._stored(year, _SEGUNDO_TURNO)
        ufs = tuple(sorted({place.uf for place in segundo.places}))
        participacoes: dict[tuple[int, str, str], tuple[int, int]] = {}
        for turno in (_PRIMEIRO_TURNO, _SEGUNDO_TURNO):
            for (uf, codigo), lida in self._participation(year, turno, ufs).items():
                participacoes[(turno, uf, chave_tse(codigo))] = lida
        origem = analisar_origem(primeiro.places, segundo.places, participacoes)
        pagina = PaginaDaOrigem(
            ano=year,
            gerado_em=self._clock(),
            origem=origem,
            cores=self._cores,
            siglas=self._siglas,
            lugares_primeiro_em=primeiro.gerado_em,
            lugares_segundo_em=segundo.gerado_em,
            carga_segundo_em=(
                None if self._last_load is None else self._last_load(year, _SEGUNDO_TURNO)
            ),
        )
        tabela = destino.with_suffix(".csv")
        gravar_texto(destino, self._render(pagina))
        gravar_texto(tabela, self._tabulate(origem))
        return PresentedOrigin(destino, tabela, self._open(destino), origem)

    def _stored(self, ano: int, turno: int) -> StoredCrossReport:
        stored = self._load(ano, turno)
        if stored is None or not stored.places:
            raise StoredRoundMissingError(ano, turno)
        return stored


def ler_marcas(caminho: Path) -> tuple[dict[int, str], dict[int, str]]:
    """Cores e siglas por número de partido. Arquivo ausente ou ilegível dá mapas vazios:
    a página usa a cor padrão e só o número."""
    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, {}
    if not isinstance(bruto, dict):
        return {}, {}
    cores: dict[int, str] = {}
    siglas: dict[int, str] = {}
    for chave, valor in bruto.items():
        if not (isinstance(chave, str) and chave.isdigit() and isinstance(valor, dict)):
            continue
        numero = int(chave)
        cor = valor.get("cor")
        sigla = valor.get("sigla")
        if isinstance(cor, str):
            cores[numero] = cor
        if isinstance(sigla, str):
            siglas[numero] = sigla
    return cores, siglas


def main(
    argv: Sequence[str] | None = None,
    *,
    load: Load | None = None,
    participation: Participation | None = None,
    last_load: LastLoad | None = None,
    open_report: OpenReport | None = None,
    clock: Clock | None = None,
    marcas: Path = _MARCAS,
) -> int:
    args = _parser().parse_args(argv)
    try:
        report = _present(args, load, participation, last_load, open_report, clock, marcas)
    except StoredRoundMissingError as error:
        print(
            f"Não há lugares gravados do {error.turno}º turno de {error.ano}. "
            "Rode antes o relatório do mapa para gravá-los.",
            file=sys.stderr,
        )
        return EXIT_FAILURE
    except FinalistsMissingError:
        print("O 2º turno gravado não tem dois finalistas.", file=sys.stderr)
        return EXIT_FAILURE
    except SchemaOutdatedError:
        print(SCHEMA_OUTDATED_HINT, file=sys.stderr)
        return EXIT_FAILURE
    except ElectionError:
        print("Não foi possível apresentar a origem dos votos.", file=sys.stderr)
        return EXIT_FAILURE
    _print_success(report)
    return EXIT_SUCCESS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mostra de onde vieram os votos novos dos finalistas no 2º turno.",
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--destino")
    parser.add_argument("--sem-navegador", action="store_true")
    return parser


def _present(
    args: argparse.Namespace,
    load: Load | None,
    participation: Participation | None,
    last_load: LastLoad | None,
    open_report: OpenReport | None,
    clock: Clock | None,
    marcas: Path,
) -> PresentedOrigin:
    destino = _destino(args)
    opener = _choose_opener(args, open_report)
    cores, siglas = ler_marcas(marcas)
    if load is not None and participation is not None:
        use_case = PresentOrigin(
            load,
            participation,
            opener,
            last_load=last_load,
            cores=cores,
            siglas=siglas,
            clock=clock,
        )
        return use_case.execute(int(args.ano), destino)
    return _production(int(args.ano), destino, opener, clock, cores, siglas)


def _production(
    ano: int,
    destino: Path,
    opener: OpenReport,
    clock: Clock | None,
    cores: Mapping[int, str],
    siglas: Mapping[int, str],
) -> PresentedOrigin:
    from eleicoes.composition.boletim import build_boletim_reader
    from eleicoes.composition.presidente_governador import build_cross_report_store

    env = _environment()
    store = build_cross_report_store(env)
    reader = build_boletim_reader(env)
    try:
        use_case = PresentOrigin(
            store.load,
            bound_participation(reader),
            opener,
            last_load=reader.last_load,
            cores=cores,
            siglas=siglas,
            clock=clock,
        )
        return use_case.execute(ano, destino)
    finally:
        reader.close()
        store.close()


def bound_participation(reader: BoletimReader) -> Participation:
    """Uma consulta por UF e turno; o leitor não repete a mesma UF."""

    def participation(
        ano: int, turno: int, ufs: tuple[str, ...]
    ) -> dict[tuple[str, str], tuple[int, int]]:
        found: dict[tuple[str, str], tuple[int, int]] = {}
        for uf in ufs:
            for linha in reader.participation(ano, turno, uf, _PRESIDENTE, _MUNICIPIO):
                found[(uf, chave_tse(str(linha.municipio)))] = (
                    linha.eleitores_aptos,
                    linha.comparecimento,
                )
        return found

    return participation


def _destino(args: argparse.Namespace) -> Path:
    if args.destino:
        return Path(str(args.destino))
    return Path("relatorios") / f"origem-votos-{args.ano}.html"


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


def _print_success(report: PresentedOrigin) -> None:
    origem = report.origem
    total = origem.total
    novos = total.novos
    print(f"Origem dos votos gravada em {report.destino} e {report.tabela}.")
    print(
        f"UFs comparadas: {', '.join(uf.uf for uf in origem.ufs)}. "
        f"Municípios: {format_integer(len(origem.municipios))}."
    )
    if origem.ufs_sem_segundo_turno:
        print(f"Sem 2º turno gravado: {', '.join(origem.ufs_sem_segundo_turno)}.")
    print(
        f"Votos novos: {format_integer(novos)} = eliminados {format_integer(total.eliminados)}"
        f" + brancos e nulos {format_integer(total.brancos_nulos_liberados)}"
        f" + comparecimento {format_integer(total.delta_comparecimento)}"
        f" (resíduo {format_integer(total.residuo)})."
    )
    for numero, delta in ((origem.a, total.delta_a), (origem.b, total.delta_b)):
        parte = "—" if novos == 0 else format_percent(Fraction(delta, novos))
        print(f"Δ{numero}: {format_integer(delta)} ({parte} dos votos novos).")
    for rotulo, dispersao in (
        ("Comparecimento", origem.por_comparecimento),
        ("Eliminados", origem.por_eliminados),
    ):
        print(
            f"{rotulo} × virada: Pearson {_decimal(dispersao.pearson)}, "
            f"Spearman {_decimal(dispersao.spearman)}, "
            f"inclinação {_decimal(dispersao.inclinacao)}."
        )
    print(
        f"Identidade: não fecha em {format_integer(len(origem.falhas))} de "
        f"{format_integer(len(origem.municipios))} municípios."
    )


def _decimal(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:.3f}".replace(".", ",")
