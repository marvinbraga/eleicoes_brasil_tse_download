import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NoReturn, cast

from dotenv import load_dotenv

from eleicoes.composition.settings import build_command
from eleicoes.composition.wiring import build_app
from eleicoes.domain.errors import (
    ElectionError,
    InvalidElectionYearError,
    InvalidPackageRefError,
    MissingElectionYearError,
    TransportError,
    UnexpectedHttpStatusError,
)
from eleicoes.domain.layout import write_index
from eleicoes.domain.report import EXIT_FAILURE, RunReport
from eleicoes.ports.download import ElectionDownloader


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        print(f"Erro: {message}", file=sys.stderr)
        raise SystemExit(EXIT_FAILURE)


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    app: ElectionDownloader | None = None,
) -> int:
    args = _parse(argv)
    try:
        command = build_command(
            _year_argument(args),
            _destino_argument(args),
            _environment(environ),
        )
        application = app if app is not None else build_app()
        report = application.execute(command)
        index = _index(command.destination, report)
    except ElectionError as error:
        print(_user_message(error), file=sys.stderr)
        return EXIT_FAILURE
    print(_render(report, index))
    return report.exit_code


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = _Parser(
        prog="eleicoes",
        description="Baixa os arquivos abertos de uma eleição do TSE.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download", help="Descobre e baixa os zips do ano informado.")
    download.add_argument(
        "--ano",
        type=int,
        default=None,
        help="Ano da eleição. Sobrescreve ANO_ELEICAO.",
    )
    download.add_argument(
        "--destino",
        default=None,
        help="Pasta de destino. Padrão: downloads/{ano} ou DIRETORIO_SAIDA.",
    )
    if argv is None:
        return parser.parse_args()
    return parser.parse_args(list(argv))


def _environment(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    if environ is not None:
        return environ
    load_dotenv()
    return os.environ


def _year_argument(args: argparse.Namespace) -> int | None:
    value = cast(object, getattr(args, "ano", None))
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise InvalidElectionYearError(value)


def _destino_argument(args: argparse.Namespace) -> str | None:
    value = cast(object, getattr(args, "destino", None))
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ElectionError("destino inválido")


def _user_message(error: ElectionError) -> str:
    if isinstance(error, InvalidElectionYearError):
        return "Ano inválido. Informe um ano entre 1994 e 2100."
    if isinstance(error, MissingElectionYearError):
        return "Informe o ano com --ano ou defina a variável ANO_ELEICAO."
    if isinstance(error, InvalidPackageRefError):
        return "A referência do conjunto de dados em TSE_DATASET_URL é inválida."
    if isinstance(error, UnexpectedHttpStatusError):
        return f"Falha ao baixar {error.filename}: HTTP {error.status_code}."
    if isinstance(error, TransportError):
        return "Falha de rede ou de disco ao acessar os arquivos do TSE."
    return "Não foi possível concluir o download."


def _index(destination: Path, report: RunReport) -> Path | None:
    if report.discovered == 0:
        return None
    return write_index(destination, report.outcomes)


def _render(report: RunReport, index: Path | None) -> str:
    if report.discovered == 0:
        return "Nenhum arquivo publicado para o ano informado."
    lines = [
        f"Arquivos encontrados: {report.discovered}",
        f"Baixados: {report.downloaded}",
        f"Ignorados: {report.skipped}",
        f"Ausentes: {report.missing}",
    ]
    if index is not None:
        lines.append(f"Índice: {index}")
    return "\n".join(lines)
