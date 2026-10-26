"""Present the section-level first × second round comparison for president."""

import argparse
import os
import sys
import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

from eleicoes.adapters.arquivo_atomico import gravar_texto
from eleicoes.adapters.csv_secoes_turnos import csv_das_secoes
from eleicoes.adapters.html_secoes_turnos import CENARIO_INICIAL, html_das_secoes
from eleicoes.domain.anomalia_secao import AnaliseSecoes, analisar_secoes
from eleicoes.domain.boletim_consulta import VotosSecao
from eleicoes.domain.errors import SCHEMA_OUTDATED_HINT, ElectionError, SchemaOutdatedError
from eleicoes.domain.mapa_turnos import FinalistsMissingError
from eleicoes.domain.percentual import format_integer
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear
from eleicoes.ports.boletim_consulta import BoletimReader
from eleicoes.ports.grade import MunicipalityNames

Render = Callable[[int, datetime, AnaliseSecoes], str]
Tabulate = Callable[[AnaliseSecoes], str]
OpenReport = Callable[[Path], bool]
Clock = Callable[[], datetime]
_PRESIDENTE: Final = "presidente"
_PRIMEIRO_TURNO: Final = 1
_SEGUNDO_TURNO: Final = 2
_APOIADO: Final = 22


class SecondRoundMissingError(ElectionError):
    def __init__(self, ano: int) -> None:
        self.ano = ano
        super().__init__(f"no second round stored for {ano}")


@dataclass(frozen=True, slots=True)
class PresentedSections:
    destino: Path
    tabela: Path
    opened: bool
    analise: AnaliseSecoes


class PresentSections:
    def __init__(
        self,
        reader: BoletimReader,
        names: MunicipalityNames,
        open_report: OpenReport,
        *,
        render: Render = html_das_secoes,
        tabulate: Tabulate = csv_das_secoes,
        clock: Clock | None = None,
        apoiado: int | None = _APOIADO,
    ) -> None:
        self._reader = reader
        self._names = names
        self._open = open_report
        self._render = render
        self._tabulate = tabulate
        self._clock = clock if clock is not None else _now
        self._apoiado = apoiado

    def execute(self, ano: int, destino: Path) -> PresentedSections:
        year = ElectionYear(ano).value
        ufs = self._reader.present_ufs(year, _SEGUNDO_TURNO, _PRESIDENTE)
        if not ufs:
            raise SecondRoundMissingError(year)
        primeiro = {uf: self._votes(year, _PRIMEIRO_TURNO, uf) for uf in ufs}
        segundo = {uf: self._votes(year, _SEGUNDO_TURNO, uf) for uf in ufs}
        nomes = {uf: self._names.names(uf) for uf in ufs}
        analise = analisar_secoes(primeiro, segundo, nomes, apoiado=self._apoiado)
        tabela = destino.with_suffix(".csv")
        destino.parent.mkdir(parents=True, exist_ok=True)
        gravar_texto(destino, self._render(year, self._clock(), analise))
        gravar_texto(tabela, self._tabulate(analise))
        return PresentedSections(destino, tabela, self._open(destino), analise)

    def _votes(self, ano: int, turno: int, uf: str) -> tuple[VotosSecao, ...]:
        return self._reader.section_votes(ano, turno, uf, _PRESIDENTE)


def main(
    argv: Sequence[str] | None = None,
    *,
    reader: BoletimReader | None = None,
    names: MunicipalityNames | None = None,
    open_report: OpenReport | None = None,
    clock: Clock | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        report = _present(args, reader, names, open_report, clock)
    except SecondRoundMissingError as error:
        print(f"Não há 2º turno de presidente gravado para {error.ano}.", file=sys.stderr)
        return EXIT_FAILURE
    except FinalistsMissingError:
        print("O 2º turno gravado não tem dois finalistas.", file=sys.stderr)
        return EXIT_FAILURE
    except SchemaOutdatedError:
        print(SCHEMA_OUTDATED_HINT, file=sys.stderr)
        return EXIT_FAILURE
    except ElectionError:
        print("Não foi possível apresentar as seções.", file=sys.stderr)
        return EXIT_FAILURE
    _print_success(report)
    return EXIT_SUCCESS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compara o 1º e o 2º turno de presidente seção por seção.",
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--destino")
    parser.add_argument("--sem-navegador", action="store_true")
    parser.add_argument(
        "--apoiado",
        type=int,
        default=_APOIADO,
        help=(
            "Finalista que os eliminados apoiaram no 2º turno."
            f" Ordena os cenários. Padrão: {_APOIADO}."
        ),
    )
    return parser


def _present(
    args: argparse.Namespace,
    reader: BoletimReader | None,
    names: MunicipalityNames | None,
    open_report: OpenReport | None,
    clock: Clock | None,
) -> PresentedSections:
    destino = _destino(args)
    opener = _choose_opener(args, open_report)
    if reader is not None and names is not None:
        use_case = PresentSections(reader, names, opener, clock=clock, apoiado=int(args.apoiado))
        return use_case.execute(int(args.ano), destino)
    return _production(int(args.ano), destino, opener, clock, int(args.apoiado))


def _production(
    ano: int,
    destino: Path,
    opener: OpenReport,
    clock: Clock | None,
    apoiado: int,
) -> PresentedSections:
    from eleicoes.composition.boletim import build_boletim_reader
    from eleicoes.composition.grade import build_municipality_names

    env = _environment()
    reader = build_boletim_reader(env)
    names = build_municipality_names(env)
    try:
        return PresentSections(reader, names, opener, clock=clock, apoiado=apoiado).execute(
            ano, destino
        )
    finally:
        reader.close()
        names.close()


def _destino(args: argparse.Namespace) -> Path:
    if args.destino:
        return Path(str(args.destino))
    return Path("relatorios") / f"secoes-turnos-{args.ano}.html"


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


def _print_success(report: PresentedSections) -> None:
    analise = report.analise
    total = analise.total
    print(f"Seções gravadas em {report.destino} e {report.tabela}.")
    print(
        f"UFs: {', '.join(resumo.uf for resumo in analise.resumos)}. "
        f"Pareadas: {format_integer(total.pareadas)}. "
        f"Só no 1º turno: {format_integer(total.so_no_primeiro)}. "
        f"Só no 2º turno: {format_integer(total.so_no_segundo)}."
    )
    for cenario, contagem in zip(analise.cenarios, total.cenarios, strict=True):
        marca = " (inicial)" if cenario.chave == CENARIO_INICIAL else ""
        print(
            f"{cenario.rotulo}{marca}: {contagem.fora} seções com |z| > 3,5"
            f" de {format_integer(contagem.com_z)}; a normal esperaria"
            f" {_decimal(contagem.fora_esperado)}."
        )


def _decimal(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")
